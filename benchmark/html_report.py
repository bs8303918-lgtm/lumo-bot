"""Generate a readable HTML dashboard for benchmark results."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from benchmark.schema import CompareResult, FieldError, PostRecord


def _esc(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value))


def _badge_bool(value: Any, *, true_label: str = "да", false_label: str = "нет") -> str:
    if value is True:
        return f'<span class="badge ok">{true_label}</span>'
    if value is False:
        return f'<span class="badge bad">{false_label}</span>'
    return '<span class="badge muted">—</span>'


def _list_items(items: Any) -> str:
    if not items or not isinstance(items, list):
        return '<span class="muted">—</span>'
    return "".join(f"<li>{_esc(x)}</li>" for x in items)


def _model_card(result: CompareResult) -> str:
    p = result.predicted or {}
    status = "error" if result.parse_error else ("ok" if result.ok else "warn")
    errors_html = ""
    if result.errors:
        items = "".join(
            f"<li><strong>{_esc(e.field)}</strong> · {_esc(e.category)}</li>" for e in result.errors
        )
        errors_html = f'<div class="errors"><div class="label">Ошибки vs golden</div><ul>{items}</ul></div>'
    parse_html = ""
    if result.parse_error:
        parse_html = f'<div class="parse-error">Parse: {_esc(result.parse_error)}</div>'

    return f"""
    <article class="model-card status-{status}">
      <header><h4>{_esc(result.model)}</h4>{parse_html}</header>
      <div class="grid-fields">
        <div><span class="label">Возможность</span>{_badge_bool(p.get('is_opportunity'))}</div>
        <div><span class="label">Категория</span><strong>{_esc(p.get('category') or '—')}</strong></div>
        <div><span class="label">Подходит профилю</span>{_badge_bool(p.get('matches_profile'))}</div>
        <div><span class="label">Допуск</span>{_badge_bool(p.get('is_eligible'))}</div>
        <div><span class="label">Дедлайн</span><code>{_esc(p.get('extracted_deadline') or '—')}</code></div>
        <div><span class="label">Название</span>{_esc(p.get('title') or '—')}</div>
      </div>
      <div class="block"><div class="label">key_benefits</div><ul>{_list_items(p.get('key_benefits'))}</ul></div>
      <div class="block"><div class="label">matched_skills</div><ul>{_list_items(p.get('matched_skills'))}</ul></div>
      <div class="block"><div class="label">red_flags</div><p>{_esc(p.get('red_flags') or '—')}</p></div>
      {errors_html}
    </article>
    """


def _post_section(post: PostRecord, results: list[CompareResult], *, profile_label: str) -> str:
    cards = "".join(_model_card(r) for r in results)
    preview = post.message_text[:280] + ("…" if len(post.message_text) > 280 else "")
    return f"""
    <section class="post-block">
      <details open>
        <summary>
          <span class="post-id">{_esc(post.id)}</span>
          <span class="post-preview">{_esc(preview)}</span>
        </summary>
        <div class="post-meta">
          <div><span class="label">Профиль</span> {_esc(profile_label)}</div>
          <div><span class="label">Канал</span> {_esc(post.source_channel or '—')}</div>
        </div>
        <pre class="post-text">{_esc(post.message_text)}</pre>
        <div class="models-grid">{cards}</div>
      </details>
    </section>
    """


def _summary_cards(summary: dict[str, Any]) -> str:
    cards = []
    for name, stats in (summary.get("by_model") or {}).items():
        total = stats.get("total", 0)
        if summary.get("mode") == "inference_only":
            cards.append(
                f'<div class="stat-card"><h3>{_esc(name)}</h3>'
                f'<p>Запросов: <strong>{total}</strong></p>'
                f'<p>Возможностей: <strong>{stats.get("opportunities_found", 0)}</strong></p>'
                f'<p>JSON ошибок: <strong>{stats.get("parse_errors", 0)}</strong></p></div>'
            )
        else:
            ok = stats.get("ok", 0)
            rate = f"{ok/total:.0%}" if total else "0%"
            cards.append(
                f'<div class="stat-card"><h3>{_esc(name)}</h3>'
                f'<p>Сравнений: <strong>{total}</strong></p>'
                f'<p>Exact match: <strong>{ok}</strong> ({rate})</p></div>'
            )
    return "".join(cards)


def write_html_report(
    *,
    output_path: Path,
    results: list[CompareResult],
    posts: list[PostRecord],
    summary: dict[str, Any],
    meta: dict[str, Any],
) -> Path:
    posts_by_id = {p.id: p for p in posts}
    grouped: dict[str, dict[str, list[CompareResult]]] = {}
    profile_labels: dict[str, str] = {}

    for row in results:
        profile_id = (row.predicted or {}).get("_profile_id") or meta.get("profile_id") or "default"
        profile_labels[profile_id] = (row.predicted or {}).get("_profile_label") or meta.get("profile_name") or profile_id
        grouped.setdefault(profile_id, {}).setdefault(row.record_id, []).append(row)

    sections: list[str] = []
    for profile_id, post_map in grouped.items():
        label = profile_labels.get(profile_id, profile_id)
        if len(grouped) > 1:
            sections.append(f'<h2 class="profile-heading">Профиль: {_esc(label)}</h2>')
        for post_id, post_results in post_map.items():
            post = posts_by_id.get(post_id) or PostRecord(id=post_id, message_text="(текст поста не загружен)")
            sections.append(_post_section(post, post_results, profile_label=label))

    agreement = summary.get("model_agreement") or {}
    agreement_html = ""
    if agreement.get("posts_with_multiple_models"):
        rows = []
        for field, stats in (agreement.get("field_agreement") or {}).items():
            u, s = stats.get("unanimous", 0), stats.get("split", 0)
            total = u + s
            pct = f"{u / total:.0%}" if total else "—"
            rows.append(f"<tr><td>{_esc(field)}</td><td>{u}/{total}</td><td>{pct}</td></tr>")
        agreement_html = (
            f'<section class="panel"><h2>Согласие моделей</h2>'
            f'<p class="muted">Постов с 2+ моделями: {agreement.get("posts_with_multiple_models")}</p>'
            f'<table><thead><tr><th>Поле</th><th>Единогласно</th><th>%</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></section>'
        )

    profile_block = ""
    if meta.get("profile_text"):
        profile_block = (
            f'<section class="panel profile-box"><h2>Профиль пользователя</h2>'
            f'<pre>{_esc(meta.get("profile_text"))}</pre></section>'
        )

    doc = f"""<!DOCTYPE html>
<html lang="ru"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lumo Benchmark — {_esc(meta.get('stage_label', 'run'))}</title>
<style>
:root {{ --bg:#0f1419; --panel:#1a2332; --text:#e7ecf3; --muted:#8b98a8; --accent:#6ea8fe; --ok:#3dd68c; --bad:#ff6b6b; --warn:#ffc857; --border:#2a3544; }}
body {{ margin:0; font-family:"Segoe UI",system-ui,sans-serif; background:var(--bg); color:var(--text); }}
.wrap {{ max-width:1200px; margin:0 auto; padding:24px 20px 80px; }}
h1 {{ margin:0 0 8px; font-size:1.6rem; }} h2 {{ font-size:1.15rem; margin:0 0 12px; }} h3,h4 {{ margin:0 0 8px; }}
.muted {{ color:var(--muted); }} .hero {{ margin-bottom:24px; padding-bottom:16px; border-bottom:1px solid var(--border); }}
.meta-row {{ display:flex; flex-wrap:wrap; gap:16px; font-size:.9rem; color:var(--muted); }}
.panel {{ background:var(--panel); border:1px solid var(--border); border-radius:12px; padding:16px; margin-bottom:20px; }}
.stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin-bottom:20px; }}
.stat-card {{ background:var(--panel); border:1px solid var(--border); border-radius:10px; padding:14px; }}
.profile-box pre {{ white-space:pre-wrap; font-size:.85rem; max-height:260px; overflow:auto; margin:0; }}
.profile-heading {{ margin:28px 0 12px; color:var(--accent); }}
details {{ background:var(--panel); border:1px solid var(--border); border-radius:12px; margin-bottom:16px; overflow:hidden; }}
summary {{ cursor:pointer; padding:14px 16px; display:flex; gap:12px; list-style:none; }}
summary::-webkit-details-marker {{ display:none; }}
.post-id {{ font-family:monospace; color:var(--accent); font-size:.85rem; }}
.post-preview {{ color:var(--muted); font-size:.9rem; }}
.post-meta {{ display:flex; flex-wrap:wrap; gap:16px; padding:0 16px 12px; font-size:.85rem; }}
.post-text {{ margin:0; padding:12px 16px; background:#121820; border-top:1px solid var(--border); border-bottom:1px solid var(--border); white-space:pre-wrap; font-size:.82rem; max-height:300px; overflow:auto; }}
.models-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:12px; padding:16px; }}
.model-card {{ background:#121820; border:1px solid var(--border); border-radius:10px; padding:12px; }}
.model-card.status-ok {{ border-color:rgba(61,214,140,.35); }}
.model-card.status-warn {{ border-color:rgba(255,200,87,.35); }}
.model-card.status-error {{ border-color:rgba(255,107,107,.45); }}
.grid-fields {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; font-size:.85rem; margin-bottom:8px; }}
.label {{ display:block; font-size:.72rem; text-transform:uppercase; color:var(--muted); margin-bottom:2px; }}
.block {{ margin-top:8px; font-size:.85rem; }} .block ul {{ margin:4px 0 0; padding-left:18px; }} .block p {{ margin:4px 0 0; }}
.badge {{ display:inline-block; padding:2px 8px; border-radius:999px; font-size:.75rem; font-weight:600; }}
.badge.ok {{ background:rgba(61,214,140,.15); color:var(--ok); }}
.badge.bad {{ background:rgba(255,107,107,.15); color:var(--bad); }}
.badge.muted {{ background:rgba(139,152,168,.15); color:var(--muted); }}
.parse-error {{ color:var(--bad); font-size:.8rem; }}
.errors {{ margin-top:8px; font-size:.8rem; color:var(--warn); border-top:1px dashed var(--border); padding-top:8px; }}
table {{ width:100%; border-collapse:collapse; font-size:.9rem; }}
th,td {{ text-align:left; padding:8px; border-bottom:1px solid var(--border); }}
</style></head><body><div class="wrap">
<div class="hero">
  <h1>Lumo LLM Benchmark</h1>
  <p class="muted">{_esc(meta.get('stage_label', ''))} · {_esc(meta.get('run_at', ''))}</p>
  <div class="meta-row">
    <span>Модели: {_esc(', '.join(meta.get('models') or []))}</span>
    <span>Постов: {meta.get('posts_count', 0)}</span>
  </div>
</div>
{profile_block}
<section class="stats">{_summary_cards(summary)}</section>
{agreement_html}
<h2 style="margin-bottom:12px">Посты × модели</h2>
{''.join(sections)}
</div></body></html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(doc, encoding="utf-8")
    return output_path


def load_results_from_jsonl(path: Path) -> list[CompareResult]:
    results: list[CompareResult] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        errors = [
            FieldError(field=e["field"], category=e["category"], expected=e.get("expected"), actual=e.get("actual"))
            for e in row.get("errors") or []
        ]
        results.append(
            CompareResult(
                record_id=row["record_id"],
                model=row["model"],
                errors=errors,
                predicted=row.get("predicted") or {},
                parse_error=row.get("parse_error"),
            )
        )
    return results

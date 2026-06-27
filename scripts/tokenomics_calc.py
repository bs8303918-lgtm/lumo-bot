"""Rough tokenomics for Lumo LLM usage."""
from __future__ import annotations

import sqlite3
import statistics
from pathlib import Path

from config import get_settings
from llm.deadline import format_today
from llm.prompts import CLASSIFICATION_PROMPT, RELEVANCE_PROMPT

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "lumo.db"

# Groq llama-3.1-8b-instant (June 2026 public pricing)
INPUT_USD_PER_M = 0.05
OUTPUT_USD_PER_M = 0.08
FREE_RPD = 14_400
FREE_TPD = 500_000
FREE_TPM = 6_000
FREE_RPM = 30

OUT_TOKENS_CLASSIFY = 250
OUT_TOKENS_RELEVANCE = 350
HEALTH_TOKENS = 10  # ping ~5 out + tiny prompt


def est_tokens(text: str) -> int:
    return max(1, len(text) // 3)


def main() -> None:
    settings = get_settings()
    interval = settings.llm_processor_interval_seconds
    batch = settings.llm_classify_batch_limit
    delay = settings.llm_request_delay_seconds
    pair_on = settings.llm_enable_pair_relevance
    max_pairs = settings.llm_max_pairs_per_cycle
    ai_limit = settings.ai_search_daily_limit

    cycles_per_day = 86_400 / interval
    max_classify_req_day = min(cycles_per_day * batch, FREE_RPD)

    today = format_today()
    cls_base = CLASSIFICATION_PROMPT.format(message_text="", today=today)
    rel_base = RELEVANCE_PROMPT.format(
        interest_query="студент IT, ищу хакатоны и стажировки в AI" * 2,
        message_text="",
        today=today,
    )

    conn = sqlite3.connect(DB)
    texts = [
        r[0]
        for r in conn.execute("SELECT text FROM raw_messages WHERE text IS NOT NULL").fetchall()
        if r[0]
    ]
    users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    channels = conn.execute("SELECT COUNT(*) FROM monitored_channels").fetchone()[0]
    try:
        daily_posts = conn.execute(
            """
            SELECT substr(fetched_at, 1, 10) AS d, COUNT(*) AS c
            FROM raw_messages
            GROUP BY 1
            ORDER BY 1 DESC
            LIMIT 14
            """
        ).fetchall()
    except sqlite3.Error:
        daily_posts = []

    cls_in = [est_tokens(cls_base) + est_tokens(t) for t in texts]
    cls_total = [x + OUT_TOKENS_CLASSIFY for x in cls_in]
    rel_in = [est_tokens(rel_base) + est_tokens(t) for t in texts]
    rel_total = [x + OUT_TOKENS_RELEVANCE for x in rel_in]

    avg_cls = statistics.mean(cls_total)
    p90_cls = sorted(cls_total)[int(len(cls_total) * 0.9)]
    avg_rel = statistics.mean(rel_total)

    avg_posts_day = (
        statistics.mean([c for _, c in daily_posts[:7]]) if daily_posts else None
    )

    # Config-limited throughput
    req_per_cycle = batch + (max_pairs if pair_on else 0)
    tokens_per_cycle_classify = batch * avg_cls
    tokens_per_cycle_pairs = max_pairs * avg_rel if pair_on else 0
    tokens_per_cycle = tokens_per_cycle_classify + tokens_per_cycle_pairs + HEALTH_TOKENS / (
        settings.llm_health_check_interval_seconds / interval
    )

    tokens_day_config = tokens_per_cycle * cycles_per_day
    req_day_config = req_per_cycle * cycles_per_day

    # Real demand scenarios
    posts_day_low, posts_day_mid, posts_day_high = 20, 50, 120
    for label, posts in [
        ("факт ~7д", avg_posts_day or posts_day_mid),
        ("низкая", posts_day_low),
        ("средняя", posts_day_mid),
        ("высокая", posts_day_high),
    ]:
        tpd = posts * avg_cls
        cost = (posts * (avg_cls - OUT_TOKENS_CLASSIFY) / 1e6 * INPUT_USD_PER_M) + (
            posts * OUT_TOKENS_CLASSIFY / 1e6 * OUTPUT_USD_PER_M
        )
        print(f"SCENARIO {label}: posts/day={posts:.0f} tokens/day={tpd:,.0f} cost=${cost:.4f}")

    print("\n=== BASELINE CONFIG ===")
    print(f"provider={settings.llm_provider} model={settings.llm_model_name}")
    print(f"interval={interval}s batch={batch} delay={delay}s pair_relevance={pair_on}")
    print(f"users={users} channels={channels} raw_messages={len(texts)}")
    print(f"avg classify tokens/post={avg_cls:.0f} p90={p90_cls:.0f}")
    print(f"avg relevance tokens/pair={avg_rel:.0f} (if enabled)")
    print(f"cycles/day={cycles_per_day:.1f} max classify req/day(config)={max_classify_req_day:.0f}")
    print(f"config ceiling tokens/day={tokens_day_config:,.0f} req/day={req_day_config:.0f}")
    print(f"AI search/user/day={ai_limit} -> LLM tokens=0 (local matcher)")
    print(f"site catalog/AI -> LLM tokens=0")
    print("\n=== GROQ FREE TIER (llama-3.1-8b-instant) ===")
    print(f"limits: {FREE_RPM} rpm, {FREE_TPM:,} tpm, {FREE_RPD:,} rpd, {FREE_TPD:,} tpd")
    posts_fit_tpd = FREE_TPD / avg_cls
    print(f"max posts/day by token cap ≈ {posts_fit_tpd:.0f}")
    print(f"max posts/day by req cap = {FREE_RPD}")
    bottleneck = min(posts_fit_tpd, FREE_RPD)
    print(f"effective free capacity ≈ {bottleneck:.0f} posts/day classify-only")
    free_cost_equiv = (bottleneck * avg_cls / 1e6) * ((avg_cls - OUT_TOKENS_CLASSIFY) / avg_cls * INPUT_USD_PER_M + OUT_TOKENS_CLASSIFY / avg_cls * OUTPUT_USD_PER_M)
    print(f"if paid, that volume ≈ ${free_cost_equiv:.2f}/day")
    print("\n=== PAID SCENARIOS / MONTH ===")
    for posts in [50, 100, 200, 500]:
        tpd = posts * avg_cls
        daily = (posts * (avg_cls - OUT_TOKENS_CLASSIFY) / 1e6 * INPUT_USD_PER_M) + (
            posts * OUT_TOKENS_CLASSIFY / 1e6 * OUTPUT_USD_PER_M
        )
        print(f"{posts:>3} posts/day -> {tpd:>9,.0f} tok/day ${daily:.3f}/day ${daily*30:.2f}/mo")

    if daily_posts:
        print("\n=== LAST DAYS POST VOLUME ===")
        for d, c in daily_posts:
            print(f"  {d}: {c}")


if __name__ == "__main__":
    main()

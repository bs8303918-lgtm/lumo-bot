"""Format benchmark reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from benchmark.compare import summarize_errors, summarize_model_agreement
from benchmark.html_report import write_html_report
from benchmark.schema import CompareResult, PostRecord


def results_to_rows(results: list[CompareResult]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in results:
        rows.append(
            {
                "record_id": row.record_id,
                "model": row.model,
                "ok": row.ok,
                "parse_error": row.parse_error,
                "predicted": row.predicted,
                "errors": [
                    {
                        "field": e.field,
                        "category": e.category,
                        "expected": e.expected,
                        "actual": e.actual,
                        "detail": e.detail,
                    }
                    for e in row.errors
                ],
            }
        )
    return rows


def print_report(summary: dict[str, Any], agreement: dict[str, Any] | None = None) -> None:
    print("\n=== Benchmark summary ===")
    if summary.get("mode") == "inference_only":
        print(f"Predictions: {summary['total_predictions']}")
        print(f"Parse errors: {summary.get('parse_errors', 0)}")
    else:
        print(f"Comparisons: {summary['total_comparisons']}")
        print(f"Exact match: {summary['exact_match']} ({summary['exact_match_rate']:.1%})")

        if summary.get("errors_by_category"):
            print("\nErrors by category:")
            for cat, count in summary["errors_by_category"].items():
                print(f"  {cat}: {count}")

        if summary.get("errors_by_field"):
            print("\nErrors by field:")
            for field, count in summary["errors_by_field"].items():
                print(f"  {field}: {count}")

        print("\nBy model:")
        for model, stats in summary.get("by_model", {}).items():
            total = stats["total"]
            ok = stats["ok"]
            rate = ok / total if total else 0
            print(f"  {model}: {ok}/{total} exact ({rate:.1%})")

    if agreement and agreement.get("posts_with_multiple_models"):
        print("\nInter-model agreement (same post, different models):")
        for field, stats in agreement.get("field_agreement", {}).items():
            u, s = stats["unanimous"], stats["split"]
            total = u + s
            if total:
                print(f"  {field}: {u}/{total} unanimous ({u/total:.0%})")


def write_report(
    results: list[CompareResult],
    *,
    output_dir: Path,
    compare_golden: bool = True,
    posts: list[PostRecord] | None = None,
    meta: dict[str, Any] | None = None,
) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    detail_path = output_dir / "benchmark_results.jsonl"
    summary_path = output_dir / "benchmark_summary.json"
    html_path = output_dir / "report.html"

    with detail_path.open("w", encoding="utf-8") as fh:
        for row in results_to_rows(results):
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    if compare_golden:
        summary: dict[str, Any] = summarize_errors(results)
    else:
        summary = {
            "mode": "inference_only",
            "total_predictions": len(results),
            "parse_errors": sum(1 for r in results if r.parse_error),
            "by_model": {},
        }
        for row in results:
            stats = summary["by_model"].setdefault(
                row.model, {"total": 0, "parse_errors": 0, "opportunities_found": 0}
            )
            stats["total"] += 1
            if row.parse_error:
                stats["parse_errors"] += 1
            if row.predicted.get("is_opportunity"):
                stats["opportunities_found"] += 1

    agreement = summarize_model_agreement(results)
    summary["model_agreement"] = agreement

    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    report_meta = dict(meta or {})
    report_meta.setdefault("detail_file", str(detail_path.name))
    write_html_report(
        output_path=html_path,
        results=results,
        posts=posts or [],
        summary=summary,
        meta=report_meta,
    )
    return detail_path, summary_path, html_path

"""Run LLM matching benchmark with HTML report."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.llm_runner import run_matching_benchmark
from benchmark.report import print_report, write_report
from benchmark.schema import (
    GoldenUserProfile,
    load_model_configs,
    load_posts_jsonl,
    load_stage2_profiles,
    load_user_profile,
)


def _env_lookup(name: str | None) -> str:
    if not name:
        return ""
    return os.environ.get(name, "").strip()


def _profiles_for_stage(args: argparse.Namespace) -> list[GoldenUserProfile]:
    if args.stage == 1:
        path = args.profile or ROOT / "data" / "benchmark" / "golden_user_ideal.json"
        return [load_user_profile(path)]
    path = args.stage2_profiles or ROOT / "data" / "benchmark" / "stage2_profiles.jsonl"
    return load_stage2_profiles(path)


async def _run_profiles(
    posts,
    profiles: list[GoldenUserProfile],
    models,
    *,
    delay: float,
    concurrent: int,
    compare_golden: bool,
) -> list:
    all_results = []
    for profile in profiles:
        print(f"\n--- Профиль: {profile.name or profile.id} ---")
        chunk = await run_matching_benchmark(
            posts,
            models,
            profile,
            request_delay=delay,
            max_concurrent=concurrent,
            compare_golden=compare_golden,
        )
        all_results.extend(chunk)
    return all_results


async def main_async(args: argparse.Namespace) -> int:
    posts_path = args.posts
    if not posts_path.is_file():
        print(f"Posts file not found: {posts_path}")
        print("Run: python scripts/export_benchmark_dataset.py --limit 200")
        return 1

    try:
        profiles = _profiles_for_stage(args)
    except (ValueError, FileNotFoundError) as exc:
        print(f"Profile error: {exc}")
        return 1

    posts = load_posts_jsonl(posts_path)
    if args.limit:
        posts = posts[: args.limit]
    if not posts:
        print("No posts to benchmark.")
        return 1

    models = load_model_configs(args.models, env_lookup=_env_lookup)
    if args.models_filter:
        allowed = set(args.models_filter)
        models = [m for m in models if m.name in allowed]
    if not models:
        print(f"No models loaded from {args.models}")
        print("Добавь ключи в .env (см. .env.example → Benchmark LLM keys)")
        return 1

    missing_keys = []
    for m in models:
        if not m.api_key:
            missing_keys.append(m.api_key_env or m.name)
    if missing_keys:
        print("Не хватает API-ключей в .env:")
        for name in missing_keys:
            print(f"  {name}=...")
        return 1

    has_golden = any(p.golden is not None for p in posts)
    compare_golden = has_golden and not args.no_golden_compare
    stage_label = f"Этап {args.stage}" + (" — идеальный профиль" if args.stage == 1 else f" — {len(profiles)} живых профилей")

    print(stage_label)
    print(f"Posts:   {posts_path} ({len(posts)} шт.)")
    print(f"Models:  {', '.join(m.name for m in models)}")

    results = await _run_profiles(
        posts,
        profiles,
        models,
        delay=args.delay,
        concurrent=args.concurrent,
        compare_golden=compare_golden,
    )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = args.output_dir / f"stage{args.stage}_{stamp}"
    profile_text = profiles[0].interest_query if len(profiles) == 1 else ""

    detail_path, summary_path, html_path = write_report(
        results,
        output_dir=out_dir,
        compare_golden=compare_golden,
        posts=posts,
        meta={
            "stage": args.stage,
            "stage_label": stage_label,
            "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "models": [m.name for m in models],
            "posts_count": len(posts),
            "profile_text": profile_text,
            "profiles_count": len(profiles),
        },
    )

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    print_report(summary, summary.get("model_agreement"))
    print(f"\nHTML отчёт (открой в браузере):\n  {html_path}")
    print(f"JSONL детали:\n  {detail_path}")
    print(f"Summary:\n  {summary_path}")

    latest = args.output_dir / "latest_report.html"
    latest.write_bytes(html_path.read_bytes())
    print(f"\nВсегда свежий:\n  {latest}")

    if args.open:
        webbrowser.open(html_path.resolve().as_uri())

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Lumo LLM benchmark + HTML report")
    parser.add_argument("--stage", type=int, choices=[1, 2], default=1, help="1=ideal profile, 2=live users")
    parser.add_argument("--posts", type=Path, default=ROOT / "data" / "benchmark" / "posts.jsonl")
    parser.add_argument("--profile", type=Path, help="Stage 1 profile JSON (default: golden_user_ideal.json)")
    parser.add_argument(
        "--stage2-profiles",
        type=Path,
        default=ROOT / "data" / "benchmark" / "stage2_profiles.jsonl",
    )
    parser.add_argument("--models", type=Path, default=ROOT / "data" / "benchmark" / "models.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "benchmark" / "results")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--models-filter", nargs="*")
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--concurrent", type=int, default=2)
    parser.add_argument("--no-golden-compare", action="store_true")
    parser.add_argument("--open", action="store_true", help="Open HTML report in browser after run")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()

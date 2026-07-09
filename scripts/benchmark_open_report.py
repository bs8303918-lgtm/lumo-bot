"""Open the latest benchmark HTML report in the browser."""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Open Lumo benchmark HTML report")
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        help="Path to report.html (default: data/benchmark/results/latest_report.html)",
    )
    args = parser.parse_args()

    if args.path:
        target = args.path
    else:
        target = ROOT / "data" / "benchmark" / "results" / "latest_report.html"

    if not target.is_file():
        print(f"Report not found: {target}")
        print("Run benchmark first:")
        print("  python scripts/benchmark_extraction.py --stage 1 --limit 5 --open")
        return 1

    url = target.resolve().as_uri()
    print(f"Opening: {target}")
    webbrowser.open(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

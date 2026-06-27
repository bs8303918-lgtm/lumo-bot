"""Проверка env на Railway / локально. Run: python scripts/check_railway_env.py"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import get_settings

KEYS = [
    "TELEGRAM_API_ID",
    "TELEGRAM_API_HASH",
    "TELEGRAM_BOT_TOKEN",
    "DATABASE_URL",
    "TELETHON_SESSION_PATH",
    "LUMO_MODE",
    "RAILWAY_ENVIRONMENT",
]


def main() -> None:
    settings = get_settings()
    print("=== Environment (raw) ===")
    for key in KEYS:
        val = os.environ.get(key)
        if val is None:
            print(f"  {key}: (не задано)")
        elif key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_API_HASH", "DATABASE_URL"):
            print(f"  {key}: *** задано, длина {len(val)} ***")
        else:
            print(f"  {key}: {val}")

    print("\n=== Settings (parsed) ===")
    print(f"  telegram_api_id: {settings.telegram_api_id!r}")
    print(f"  telegram_api_hash: {'задан' if settings.telegram_api_hash.strip() else 'ПУСТО'}")
    print(f"  database_url starts with: {settings.database_url[:40]}...")
    print(f"  lumo_mode: {settings.lumo_mode}")
    print(f"  is_railway: {settings.is_railway}")


if __name__ == "__main__":
    main()

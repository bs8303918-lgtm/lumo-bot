"""Удаляет битую Telethon-сессию. Run: python scripts/reset_telethon_session.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import get_settings


def main() -> None:
    settings = get_settings()
    base = settings.telethon_session_path
    removed = []
    for path in [Path(f"{base}.session"), Path(f"{base}.session-journal")]:
        if path.exists():
            path.unlink()
            removed.append(path.name)
    if removed:
        print("Удалено:", ", ".join(removed))
    else:
        print("Файлы сессии не найдены (уже чисто).")
    print("\nТеперь выполните (рекомендуется QR):")
    print("  python scripts/telethon_login_qr.py")


if __name__ == "__main__":
    main()

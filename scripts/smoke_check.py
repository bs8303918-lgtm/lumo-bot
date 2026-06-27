"""Быстрая проверка: конфиг, БД, LLM, Telethon. Без запуска бота."""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import get_settings
from db.base import async_session_factory
from llm.client import LLMClient
from monitor.telethon_client import telethon_is_authorized
from sqlalchemy import text


async def main() -> int:
    settings = get_settings()
    ok = True

    print("=== Lumo smoke check ===\n")

    # Config
    print(f"LLM provider: {settings.llm_provider}")
    print(f"LLM model:    {settings.llm_model_name}")
    if settings.llm_configured:
        print("LLM key:      set")
    else:
        print("LLM key:      MISSING")
        ok = False

    if settings.telegram_bot_token:
        print("Bot token:    set")
    else:
        print("Bot token:    MISSING")
        ok = False

    # Database
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        print("Database:     ok")
    except Exception as exc:
        print(f"Database:     FAIL ({exc})")
        ok = False

    # LLM
    if settings.llm_configured:
        llm_ok = await LLMClient().health_check()
        print(f"LLM API:      {'ok' if llm_ok else 'FAIL (quota/key/model)'}")
        ok = ok and llm_ok
    else:
        print("LLM API:      skipped")

    # Telethon
    try:
        telethon_ok = await telethon_is_authorized()
        print(f"Telethon:     {'logged in' if telethon_ok else 'not logged in'}")
        if not telethon_ok:
            print("              -> run: .venv\\Scripts\\python scripts\\telethon_login_qr.py")
            ok = False
    except Exception as exc:
        print(f"Telethon:     FAIL ({exc})")
        ok = False

    print()
    if ok:
        print("All checks passed. Run: .venv\\Scripts\\python main.py")
        return 0
    print("Some checks failed. Fix issues above before running main.py")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

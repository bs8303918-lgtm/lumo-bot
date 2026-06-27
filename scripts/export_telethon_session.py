"""Экспорт Telethon-сессии в строку для Railway Variables.

1. Локально залогинься: python scripts/telethon_login_qr.py
2. Запусти этот скрипт
3. Скопируй строку в Railway → TELETHON_SESSION_STRING (секрет, НЕ в GitHub)
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telethon.sessions import StringSession

from monitor.telethon_client import get_telethon_client, reset_client


async def main() -> None:
    reset_client()
    client = get_telethon_client()
    await client.connect()
    if not await client.is_user_authorized():
        print("Telethon не залогинен. Сначала: python scripts/telethon_login_qr.py")
        return

    session_string = StringSession.save(client.session)
    await client.disconnect()

    print("\n" + "=" * 60)
    print("TELETHON_SESSION_STRING — скопируй в Railway Variables:")
    print("=" * 60)
    print(session_string)
    print("=" * 60)
    print("\nRailway → lumo-bot → Variables → New Variable")
    print("  Name:  TELETHON_SESSION_STRING")
    print("  Value: (вставь строку выше целиком)")
    print("\n⚠️  НЕ коммить в GitHub — это доступ к твоему Telegram.")
    print("После Redeploy Volume для Telethon не нужен.\n")


if __name__ == "__main__":
    asyncio.run(main())

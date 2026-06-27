"""Повторный логин с отправкой кода по SMS. Run: python scripts/telethon_login_sms.py"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telethon.errors import SessionPasswordNeededError

from config import get_settings
from monitor.telethon_client import get_telethon_client


async def main() -> None:
    settings = get_settings()
    client = get_telethon_client()
    await client.connect()

    if await client.is_user_authorized():
        print("Сессия уже активна.")
        return

    print(f"Отправляю код по SMS на {settings.telegram_phone}...")
    await client.send_code_request(settings.telegram_phone, force_sms=True)

    code = input("Введите код из SMS: ").strip()
    try:
        await client.sign_in(settings.telegram_phone, code)
    except SessionPasswordNeededError:
        password = input("Облачный пароль (2FA): ").strip()
        await client.sign_in(password=password)

    print("Готово! Сессия сохранена.")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

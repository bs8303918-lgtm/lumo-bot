"""One-time Telethon login by phone code. Prefer QR: python scripts/telethon_login_qr.py"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telethon.errors import SessionPasswordNeededError

from config import get_settings
from monitor.telethon_client import get_telethon_client


async def main() -> None:
    settings = get_settings()
    if not settings.telegram_phone:
        print("Ошибка: заполните TELEGRAM_PHONE в .env (например +77477783925)")
        return
    if not settings.telegram_api_id or not settings.telegram_api_hash:
        print("Ошибка: заполните TELEGRAM_API_ID и TELEGRAM_API_HASH в .env")
        return

    print(f"Номер: {settings.telegram_phone}")
    client = get_telethon_client()
    await client.connect()

    if await client.is_user_authorized():
        print("Сессия уже активна — Telethon залогинен.")
        return

    print("\nКод приходит НЕ в SMS, а в приложение Telegram:")
    print("  → откройте Telegram на телефоне")
    print("  → чат «Telegram» (служебные уведомления)")
    print("  → там будет код входа\n")

    await client.send_code_request(settings.telegram_phone)

    code = input("Введите код из Telegram: ").strip()
    if not code:
        print("Код пустой. Запустите скрипт снова.")
        return

    try:
        await client.sign_in(settings.telegram_phone, code)
    except SessionPasswordNeededError:
        password = input("У вас включён облачный пароль (2FA). Введите его: ").strip()
        await client.sign_in(password=password)
    except Exception as exc:
        print(f"\nОшибка входа: {exc}")
        print("\nПопробуйте вход через QR (без кода):")
        print("  python scripts/telethon_login_qr.py")
        return

    print("\nГотово! Сессия сохранена. Можно запускать main.py")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

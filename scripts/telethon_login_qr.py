"""Вход в Telethon через QR-код (без SMS). Run: python scripts/telethon_login_qr.py"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import qrcode
from telethon.errors import SessionPasswordNeededError

from config import get_settings
from monitor.telethon_client import get_telethon_client, reset_client


QR_PATH = Path(__file__).resolve().parent.parent / "telethon_qr.png"


def show_qr(url: str) -> None:
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)

    img = qrcode.make(url)
    img.save(QR_PATH)
    print(f"\nQR-код сохранён: {QR_PATH}")

    open_file = getattr(os, "startfile", None)
    if open_file is not None:
        try:
            open_file(QR_PATH)
            print("Картинка открыта автоматически.")
            return
        except OSError:
            pass

    print("Сканируй QR ниже (Railway Shell) или используй tg:// ссылку:")
    qr.print_ascii(invert=True)
    print("Или вставь tg:// ссылку на https://www.qr-code-generator.com/")


async def main() -> None:
    settings = get_settings()
    api_hash = (settings.telegram_api_hash or "").strip()
    if not settings.telegram_api_id or not api_hash:
        print("Ошибка: TELEGRAM_API_ID и TELEGRAM_API_HASH не найдены.")
        print(f"  telegram_api_id = {settings.telegram_api_id!r}")
        print(f"  TELEGRAM_API_ID (env) = {os.environ.get('TELEGRAM_API_ID')!r}")
        print(f"  TELEGRAM_API_HASH (env) = {'задан' if os.environ.get('TELEGRAM_API_HASH') else 'НЕТ'}")
        print(
            "\nRailway: Variables должны быть у сервиса lumo-bot "
            "(имена TELEGRAM_API_ID и TELEGRAM_API_HASH), затем Redeploy."
        )
        print("Shell открывай только когда деплой Online (не FAILED).")
        print("Локально: те же ключи в .env рядом с main.py")
        return

    reset_client()
    client = get_telethon_client()
    await client.connect()

    if await client.is_user_authorized():
        print("Сессия уже активна — Telethon залогинен.")
        await client.disconnect()
        return

    print("=" * 50)
    print("ВХОД ЧЕРЕЗ QR-КОД")
    print("=" * 50)
    print("\nНа телефоне:")
    print("  Telegram → Настройки → Устройства")
    print("  → Подключить устройство → Отсканировать QR\n")
    print("Ожидаю сканирование (QR обновляется каждые 25 сек)...\n")

    while True:
        qr_login = await client.qr_login()
        show_qr(qr_login.url)
        print(f"\nСсылка для QR (можно открыть на другом устройстве):\n{qr_login.url}\n")

        try:
            user = await asyncio.wait_for(qr_login.wait(), timeout=25.0)
            name = getattr(user, "first_name", None) or getattr(user, "username", "user")
            print(f"\nВход выполнен: {name}")
            break
        except asyncio.TimeoutError:
            print("QR истёк, генерирую новый...")
            try:
                await qr_login.recreate()
            except Exception:
                qr_login = await client.qr_login()
        except SessionPasswordNeededError:
            password = input("\nВключён облачный пароль (2FA). Введите его: ").strip()
            await client.sign_in(password=password)
            print("2FA принят.")
            break
        except Exception as exc:
            print(f"\nОшибка: {exc}")
            print("Попробуйте сначала: python scripts/reset_telethon_session.py")
            await client.disconnect()
            return

    if QR_PATH.exists():
        QR_PATH.unlink(missing_ok=True)

    await client.disconnect()
    print("\nГотово! Сессия сохранена.")
    print("Теперь запускайте: python main.py")


if __name__ == "__main__":
    asyncio.run(main())

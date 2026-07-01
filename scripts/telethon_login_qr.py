"""Вход в Telethon через QR-код (без SMS). Run: python scripts/telethon_login_qr.py"""
import asyncio
import os
import signal
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import qrcode
from telethon.errors import SessionPasswordNeededError

from config import get_settings
from monitor.telethon_client import get_telethon_client, prepare_telethon_session_path, reset_client


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


def stop_main_processes() -> int:
    """Остановить main.py / uvicorn в этом контейнере (Railway Shell, без pkill)."""
    my_pid = os.getpid()
    killed = 0
    proc_root = Path("/proc")
    if not proc_root.is_dir():
        return 0

    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid == my_pid:
            continue
        try:
            cmdline = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", errors="ignore")
        except OSError:
            continue
        if "main.py" not in cmdline and not ("uvicorn" in cmdline and "api.app" in cmdline):
            continue
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"  остановлен pid {pid}: {cmdline.strip()[:100]}")
            killed += 1
        except OSError as exc:
            print(f"  не удалось остановить pid {pid}: {exc}")
    return killed


def _railway_lock_help() -> None:
    print(
        "\nСессия занята main.py. Запусти снова — скрипт сам остановит бот:\n"
        "  python scripts/telethon_login_qr.py --stop-main\n"
        "После успешного входа — Redeploy сервиса в панели Railway.\n"
    )


async def connect_client(client, *, attempts: int = 15, delay: float = 2.0) -> None:
    for attempt in range(attempts):
        try:
            await client.connect()
            return
        except sqlite3.OperationalError as exc:
            if "database is locked" not in str(exc).lower():
                raise
            if attempt == 0:
                print("database is locked — сессию держит другой процесс (main.py)...")
            if attempt >= attempts - 1:
                _railway_lock_help()
                raise
            print(f"  жду {delay}s, попытка {attempt + 2}/{attempts}...")
            await asyncio.sleep(delay)


async def main() -> None:
    if "--stop-main" in sys.argv or os.environ.get("RAILWAY_ENVIRONMENT"):
        print("Останавливаю main.py перед Telethon login...")
        n = stop_main_processes()
        if n:
            print(f"Остановлено процессов: {n}, жду 3 сек...\n")
            time.sleep(3)
        else:
            print("main.py не найден (уже остановлен?)\n")

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
    session_path = prepare_telethon_session_path()
    print(f"Сессия Telethon: {session_path}.session")
    if os.environ.get("RAILWAY_ENVIRONMENT"):
        print("Railway: если будет database is locked — см. инструкцию в конце или ниже.\n")
    try:
        client = get_telethon_client()
    except ValueError as exc:
        if "too many values to unpack" in str(exc).lower():
            print(
                "\nБитая или устаревшая файловая сессия (разные версии Telethon).\n"
                "  python scripts/reset_telethon_session.py\n"
                "  pip install -r requirements.txt\n"
                "  python scripts/telethon_login_qr.py\n"
            )
            return
        raise
    await connect_client(client)

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
    if os.environ.get("RAILWAY_ENVIRONMENT"):
        print("Redeploy сервис lumo-bot в Railway, чтобы бот снова запустился с новой сессией.")
        print("Или экспортируй строку локально: python scripts/export_telethon_session.py")
    else:
        print("Экспорт для Railway: python scripts/export_telethon_session.py")
        print("Теперь запускайте: python main.py")


if __name__ == "__main__":
    asyncio.run(main())

"""Один цикл мониторинга Telegram-каналов. Run: python scripts/run_monitor_once.py"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from monitor.telethon_client import telethon_is_authorized
from monitor.worker import MonitorWorker


async def main() -> None:
    if not await telethon_is_authorized():
        print("Telethon не залогинен. Задай TELETHON_SESSION_STRING в Railway Variables.")
        return
    print("Запуск monitor cycle…")
    await MonitorWorker().run_cycle()
    print("Готово. LLM processor добавит посты в каталог (~20 мин).")


if __name__ == "__main__":
    asyncio.run(main())

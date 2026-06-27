"""Фактический отчёт: куда уходят LLM-токены (оценка по БД)."""
from __future__ import annotations

import sqlite3
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "lumo.db"

from config import get_settings  # noqa: E402
from llm.deadline import format_today  # noqa: E402
from llm.prompts import CLASSIFICATION_PROMPT, RELEVANCE_PROMPT  # noqa: E402

FREE_TPD = 500_000
FREE_RPD = 14_400
OUT_CLASSIFY = 250
OUT_RELEVANCE = 350


def est_tokens(text: str) -> int:
    return max(1, len(text) // 3)


def main() -> None:
    settings = get_settings()
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    users = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
    with_interest = conn.execute(
        "SELECT COUNT(*) c FROM users WHERE interest_query IS NOT NULL AND interest_query != ''"
    ).fetchone()["c"]
    raw_total = conn.execute("SELECT COUNT(*) c FROM raw_messages").fetchone()["c"]
    catalog_total = conn.execute("SELECT COUNT(*) c FROM catalog_opportunities").fetchone()["c"]
    catalog_active = conn.execute(
        "SELECT COUNT(*) c FROM catalog_opportunities WHERE is_active=1"
    ).fetchone()["c"]

    daily_raw = conn.execute(
        """
        SELECT substr(fetched_at, 1, 10) AS d, COUNT(*) AS c
        FROM raw_messages
        GROUP BY 1 ORDER BY 1 DESC LIMIT 7
        """
    ).fetchall()

    daily_cls = conn.execute(
        """
        SELECT substr(classified_at, 1, 10) AS d, COUNT(*) AS c
        FROM catalog_opportunities
        WHERE classified_at IS NOT NULL
        GROUP BY 1 ORDER BY 1 DESC LIMIT 7
        """
    ).fetchall()

    texts = [
        r[0]
        for r in conn.execute("SELECT text FROM raw_messages WHERE text IS NOT NULL").fetchall()
        if r[0]
    ]
    cls_base = CLASSIFICATION_PROMPT.format(message_text="", today=format_today())
    cls_totals = [est_tokens(cls_base) + est_tokens(t) + OUT_CLASSIFY for t in texts]
    avg_cls = statistics.mean(cls_totals) if cls_totals else 1200

    # LLM classify calls ≈ записи в каталоге (каждый пост прошёл classify или spam filter без LLM)
    # Точнее: training_samples task=classify если есть
    llm_classify_est = catalog_total
    try:
        llm_classify_est = conn.execute(
            "SELECT COUNT(*) c FROM training_samples WHERE task='classify' AND model_name IS NOT NULL"
        ).fetchone()["c"]
    except sqlite3.Error:
        pass

    total_tokens_est = int(llm_classify_est * avg_cls)

    posts_7d = sum(r["c"] for r in daily_raw[:7]) if daily_raw else 0
    posts_today = daily_raw[0]["c"] if daily_raw else 0
    cls_today = daily_cls[0]["c"] if daily_cls else 0
    tokens_today_est = int(cls_today * avg_cls)
    tokens_7d_est = int(sum(r["c"] for r in daily_cls[:7]) * avg_cls) if daily_cls else 0

    pair_on = settings.llm_enable_pair_relevance
    interval = settings.llm_processor_interval_seconds
    batch = settings.llm_classify_batch_limit
    cycles_day = 86400 / interval
    max_cls_day = min(cycles_day * batch, FREE_RPD)

    print("=== ТВОЙ LUMO — РАСХОД LLM ===")
    print(f"Провайдер: {settings.llm_provider} / {settings.llm_model_name}")
    print(f"pair_relevance (дорогой режим): {'ВКЛ' if pair_on else 'ВЫКЛ'}")
    print()
    print("--- База ---")
    print(f"Пользователей: {users} (с интересом: {with_interest})")
    print(f"Постов из каналов: {raw_total}")
    print(f"Каталог (классифицировано): {catalog_total} (активных: {catalog_active})")
    print()
    print("--- Куда тратятся токены ---")
    print("1) /set_interest (профиль юзера)     -> 0 токенов (локальный матч)")
    print("2) AI-поиск на сайте                 -> 0 токенов (локальный матч)")
    print("3) Классификация постов из каналов   -> ~{:.0f} tok/пост".format(avg_cls))
    if pair_on:
        print("4) Pair relevance (юзер x пост)    -> ~1700 tok/пара (ВКЛ!)")
    else:
        print("4) Pair relevance                  -> 0 (выключен)")
    print("5) Health ping                     -> ~10 tok (редко)")
    print()
    print("--- Оценка расхода (по БД) ---")
    print(f"Всего за всё время: ~{total_tokens_est:,} tok (~{llm_classify_est} LLM-классификаций)")
    print(f"Сегодня классиф.: {cls_today} постов -> ~{tokens_today_est:,} tok")
    print(f"За 7 дней класс.: ~{tokens_7d_est:,} tok")
    print()
    print("--- Лимит Groq Free (llama-3.1-8b) ---")
    print(f"500 000 tok/день | 14 400 запросов/день")
    remain_today = max(0, FREE_TPD - tokens_today_est)
    posts_left = int(remain_today / avg_cls) if avg_cls else 0
    print(f"Сегодня использовано ~{tokens_today_est:,} / 500 000 ({tokens_today_est/5000:.1f}%)")
    print(f"Осталось сегодня ~{remain_today:,} tok (~{posts_left} постов)")
    print(f"Конфиг: цикл каждые {interval}s, batch={batch} -> до {max_cls_day:.0f} classify/день")
    print()
    print("--- Посты по дням ---")
    for r in daily_raw:
        print(f"  {r['d']}: {r['c']} новых постов")
    print("--- Классификация по дням ---")
    for r in daily_cls:
        print(f"  {r['d']}: {r['c']} -> ~{int(r['c']*avg_cls):,} tok")
    print()
    print("Groq dashboard: https://console.groq.com/settings/usage")
    print("(бот сам токены не считает — цифры оценка по длине постов)")


if __name__ == "__main__":
    main()

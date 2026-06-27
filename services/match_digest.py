import logging
import re
from dataclasses import dataclass

from config import get_settings
from services.interest_matcher import CATEGORY_DISPLAY

logger = logging.getLogger(__name__)

_buffer: "MatchDigestBuffer | None" = None


@dataclass
class PendingMatch:
    match_id: int
    card_data: dict


def get_digest_buffer() -> "MatchDigestBuffer":
    global _buffer
    if _buffer is None:
        _buffer = MatchDigestBuffer(get_settings().notification_digest_size)
    return _buffer


TYPE_LABEL: dict[str, str] = {
    "грант": "Грант",
    "стипендия": "Стипендия",
    "хакатон": "Хакатон",
    "стажировка": "Стажировка",
    "конкурс": "Конкурс",
    "олимпиада": "Олимпиада",
    "эссе": "Эссе",
    "кейс": "Кейс-чемпионат",
    "летняя_школа": "Летняя школа",
    "курс": "Курс",
    "мероприятие": "Мероприятие",
    "другое": "Возможность",
}


def _format_deadline_line(deadline: str | None) -> str:
    if not deadline or deadline.strip().lower() in ("не указан", "—", "-", "null"):
        return "📅 дедлайн не указан"
    text = deadline.strip()
    if re.match(r"\d{1,2}\.\d{1,2}\.\d{4}", text):
        return f"📅 до {text}"
    return f"📅 {text}"


def format_digest_message(items: list[dict]) -> str:
    count = len(items)
    if count == 1:
        header = "✨ Lumo · одна возможность под твой профиль\n"
    else:
        header = f"✨ Lumo · подборка из {count} возможностей\n"

    lines = [header]
    for idx, card in enumerate(items, start=1):
        opp_type = (card.get("type") or "другое").lower()
        emoji, _ = CATEGORY_DISPLAY.get(opp_type, ("📌", opp_type))
        type_label = TYPE_LABEL.get(opp_type, "Возможность")
        title = (card.get("title") or "Без названия").strip()
        link = (card.get("message_link") or "").strip()

        lines.append(f"{idx}. {emoji} {type_label}")
        lines.append(f"   «{title}»")
        lines.append(f"   {_format_deadline_line(card.get('deadline'))}")
        if link:
            lines.append(f"   👉 {link}")
        if idx < count:
            lines.append("")

    lines.append("\n—\nПодобрано под твои интересы. Новая подборка — не чаще раза в полдня.")
    return "\n".join(lines)


class MatchDigestBuffer:
    def __init__(self, batch_size: int):
        self.batch_size = max(1, batch_size)
        self._pending: dict[int, list[PendingMatch]] = {}
        self._telegram_ids: dict[int, int] = {}

    def add(self, user_id: int, telegram_id: int, match_id: int, card_data: dict) -> None:
        self._telegram_ids[user_id] = telegram_id
        self._pending.setdefault(user_id, []).append(PendingMatch(match_id, card_data))

    def pending_count(self, user_id: int) -> int:
        return len(self._pending.get(user_id, []))

    async def flush_ready(self, user_id: int, notification_service) -> int:
        """Отправить полные пачки по batch_size."""
        sent = 0
        while self.pending_count(user_id) >= self.batch_size:
            batch = self._pending[user_id][: self.batch_size]
            self._pending[user_id] = self._pending[user_id][self.batch_size :]
            if not self._pending[user_id]:
                self._pending.pop(user_id, None)
            ok = await notification_service.send_digest(
                self._telegram_ids[user_id],
                batch,
                user_id=user_id,
            )
            if ok:
                sent += len(batch)
            else:
                self._pending.setdefault(user_id, []).extend(batch)
                return sent
        return sent

    async def flush_remaining(
        self,
        user_id: int,
        notification_service,
        *,
        max_items: int | None = None,
    ) -> int:
        """Отправить остаток (< batch_size) — одним сообщением, не больше max_items."""
        items = self._pending.pop(user_id, [])
        if not items:
            return 0
        if max_items is not None and max_items > 0:
            overflow = items[max_items:]
            items = items[:max_items]
            if overflow:
                self._pending.setdefault(user_id, []).extend(overflow)
        ok = await notification_service.send_digest(
            self._telegram_ids[user_id],
            items,
            user_id=user_id,
        )
        if not ok:
            self._pending.setdefault(user_id, []).extend(items)
            return 0
        return len(items)

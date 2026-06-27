"""Предметные области (сферы) — отдельно от типов возможностей."""

from __future__ import annotations

import json
import re

# slug -> (emoji, label)
DOMAIN_DISPLAY: dict[str, tuple[str, str]] = {
    "стартапы": ("🚀", "Стартапы"),
    "it": ("💻", "IT"),
    "дизайн": ("🎨", "Дизайн"),
    "экология": ("🌿", "Экология"),
    "журналистика": ("📰", "Журналистика"),
    "медиа": ("🎬", "Медиа"),
    "биотех": ("🧬", "Биотех"),
    "биология": ("🔬", "Биология"),
    "астрофизика": ("🌌", "Астрофизика"),
    "физика": ("⚛️", "Физика"),
    "математика": ("📐", "Математика"),
    "информатика": ("🖥", "Информатика"),
    "химия": ("⚗️", "Химия"),
    "медицина": ("🏥", "Медицина"),
    "экономика": ("📊", "Экономика"),
    "финансы": ("💹", "Финансы"),
    "бизнес": ("💼", "Бизнес"),
    "психология": ("🧠", "Психология"),
    "stem": ("🔭", "STEM"),
    "инженерия": ("⚙️", "Инженерия"),
    "робототехника": ("🤖", "Робототехника"),
    "кибербезопасность": ("🔐", "Кибербезопасность"),
    "edtech": ("📱", "EdTech"),
    "medtech": ("🩺", "MedTech"),
    "femtech": ("👩‍💻", "FemTech"),
    "география": ("🗺", "География"),
    "политология": ("🏛", "Политология"),
    "философия": ("📚", "Философия"),
    "социология": ("👥", "Социология"),
    "искусство": ("🎭", "Искусство"),
    "нейронаука": ("🧬", "Нейронаука"),
    "статистика": ("📈", "Статистика"),
    "лингвистика": ("🗣", "Лингвистика"),
    "право": ("⚖️", "Право"),
    "архитектура": ("🏗", "Архитектура"),
    "сельское хозяйство": ("🌾", "Агро"),
    "спорт": ("🏅", "Спорт"),
    "музыка": ("🎵", "Музыка"),
    "кино": ("🎥", "Кино"),
    "денежные призы": ("💵", "Денежные призы"),
}

DOMAIN_TAG_RULES: tuple[tuple[str, str], ...] = (
    (r"стартап|startup|стартапер|founder|фаундер|питч\b|pitch\b|акселератор|accelerator|инкубатор|incubator", "стартапы"),
    (r"\bit\b|tech|разработ|developer|программ|software|cs major|computer science", "it"),
    (r"дизайн|design|ux|ui\b|figma|brand", "дизайн"),
    (r"эко|ecology|climate|green|устойчив|биотехнолог|clean tech", "экология"),
    (r"журналist|journalis|редактор|репорт", "журналистика"),
    (r"медиа|media\b|видеоблог|контент", "медиа"),
    (r"биотех|biotech|биотехнолог", "биотех"),
    (r"биолог|biology|олимпиадн.{0,12}биолог", "биология"),
    (r"астрофиз|astrophys|космос|space\b", "астрофизика"),
    (r"физик|physics|физмат", "физика"),
    (r"математ|math\b|olympiad math|imo\b", "математика"),
    (r"информат|informatics|informatics|олимпиад.{0,12}информ", "информатика"),
    (r"хими|chemistry|хим инжен", "химия"),
    (r"медиц|medicine|dentistr|neurobiolog|стоматolog|healthcare", "медицина"),
    (r"эконом|econom|finance|финанс|invest|инвест", "экономика"),
    (r"финанс|finance|cfa|trading", "финансы"),
    (r"бизнес|business|предприним|entrepreneur|mba\b", "бизнес"),
    (r"психолог|psycholog", "психология"),
    (r"\bstem\b|engineering|engineer", "stem"),
    (r"инженер|robot|робототех|robotics", "инженерия"),
    (r"робот|robotics", "робототехника"),
    (r"кибербез|cybersec|infosec|безопасност", "кибербезопасность"),
    (r"edtech|ed tech|образовательн.{0,8}tech", "edtech"),
    (r"medtech|med tech", "medtech"),
    (r"femtech|women.{0,8}tech", "femtech"),
    (r"географ|geograph", "география"),
    (r"политолог|politic|ir\b|международ", "политология"),
    (r"философ|philosoph", "философия"),
    (r"социолог|sociolog", "социология"),
    (r"искусств|arts\b|фото|photograph|графическ", "искусство"),
    (r"neuroscience|нейронаук|neurobiolog", "нейронаука"),
    (r"statistic|статистик", "статистика"),
    (r"лингвист|linguist", "лингвистика"),
    (r"право|law\b|юрид", "право"),
    (r"архитект|architect", "архитектура"),
    (r"агро|agri|farming|сельск", "сельское хозяйство"),
    (r"спорт|sport|athlet", "спорт"),
    (r"музык|music", "музыка"),
    (r"кино|cinema|film\b", "кино"),
    (
        r"денежн.{0,8}приз|cash prize|prize money|monetary prize|"
        r"призов.{0,10}(?:фонд|ден|₸|тенге|\$)|"
        r"выигра.{0,12}(?:деньг|приз|₸|тенге)|"
        r"награда.{0,20}(?:₸|тенге|\$|€|usd|eur)|"
        r"деньг.{0,6}(?:приз|наград)|"
        r"приз.{0,6}(?:деньг|₸|тенге|\$)",
        "денежные призы",
    ),
)

_APPROVED_DOMAINS_KEY = "approved_interest_domains_json"


def all_known_domain_slugs() -> set[str]:
    return set(DOMAIN_DISPLAY.keys())


def extract_domains_from_text(text: str) -> list[str]:
    lowered = (text or "").lower()
    found: list[str] = []
    for pattern, slug in DOMAIN_TAG_RULES:
        if re.search(pattern, lowered, flags=re.I):
            if slug not in found:
                found.append(slug)
    return found[:6]


def parse_approved_domains(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x).lower().strip() for x in data if x]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def merge_approved_domains(base: list[str], approved: list[str]) -> list[str]:
    merged = list(base)
    for item in approved:
        slug = item.lower().strip()
        if slug and slug not in merged:
            merged.append(slug)
    return merged


def display_for_domain(slug: str) -> tuple[str, str]:
    key = slug.lower().strip()
    if key in DOMAIN_DISPLAY:
        return DOMAIN_DISPLAY[key]
    label = key.replace("_", " ").capitalize()
    return ("🏷", label)


def suggest_unknown_domains(text: str, *, approved: list[str] | None = None) -> list[str]:
    """Темы из текста, которых нет в словаре — на согласование админу."""
    lowered = (text or "").lower()
    known = all_known_domain_slugs() | set(approved or [])
    already = set(extract_domains_from_text(text))
    candidates: list[str] = []

    for token in re.findall(r"[\w\-]{4,}", lowered, flags=re.UNICODE):
        token = token.strip("-_")
        if len(token) < 4:
            continue
        if token.isdigit():
            continue
        if token in {
            "класс",
            "класса",
            "классе",
            "школьник",
            "школьница",
            "студент",
            "ученик",
            "ученица",
            "ищу",
            "хочу",
            "любые",
            "online",
            "offline",
            "онлайн",
            "офлайн",
            "можно",
            "нужны",
            "нужен",
            "интерес",
            "интересуюсь",
            "интересует",
            "програм",
            "программы",
            "возможност",
            "конкурсы",
            "конкурс",
            "гранты",
            "грант",
            "хакатоны",
            "хакатон",
            "стажировки",
            "стажировка",
            "олимпиады",
            "олимпиада",
            "мероприятия",
            "мероприятие",
            "казахстан",
            "алматы",
            "астана",
            "intern",
            "junior",
            "major",
            "freshman",
            "school",
            "summer",
            "course",
            "courses",
            "contest",
            "competition",
            "research",
            "ресерч",
            "portfolio",
            "портфолио",
            "закончила",
            "закончил",
            "перехожу",
            "переходу",
            "учусь",
            "ученик",
            "ученица",
            "классе",
            "только",
            "желательно",
            "подходит",
            "подойдут",
            "также",
            "тому",
            "подобное",
            "любые",
            "любой",
            "любая",
            "media",
            "essay",
        }:
            continue
        if any(token in d or d in token for d in known):
            continue
        if token in already:
            continue
        if any(token in d or d in token for d in already):
            continue
        # только латиница / neologism — реже ложные срабатывания на русские слова
        if not re.search(r"[a-z]", token):
            continue
        if token not in candidates:
            candidates.append(token)

    return candidates[:5]

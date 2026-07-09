from llm.spam_filter import (
    is_invalid_opportunity_extraction,
    is_likely_product_feature_news,
    is_likely_spam_or_ad,
)
from services.interest_matcher import build_opportunity_tags
from services.opportunity_type import is_startup_pitch_competition, refine_opportunity_type

WHATSAPP_NICKNAME_NEWS = """
Выбор ника на WhatsApp

Теперь можно заранее выбрать ник — когда функция запустится,
другие будут видеть имя пользователя вместо номера телефона.
"""

STARTUP_BATTLE = """
STARTUP BATTLE на 500к₸ от LaunchZone

Для школьников и студентов. Подайте заявку на питч своего стартапа.
Регистрация: https://launchzone.kz/apply
Дедлайн: 20.08.2026
"""

REAL_ESSAY_CONTEST = """
Конкурс эссе для школьников 9–11 классов.
Тема: «Моя профессия будущего».
Дедлайн: 01.09.2026
Подать работу: https://example.kz/essay
"""


def test_whatsapp_nickname_is_product_news():
    is_news, reason = is_likely_product_feature_news(WHATSAPP_NICKNAME_NEWS)
    assert is_news is True
    assert reason == "product_feature_news"


def test_whatsapp_nickname_blocked_before_catalog():
    is_spam, _ = is_likely_spam_or_ad(WHATSAPP_NICKNAME_NEWS)
    assert is_spam is True


def test_whatsapp_nickname_invalid_extraction():
    invalid, reason = is_invalid_opportunity_extraction(
        {
            "is_opportunity": True,
            "title": "Выбор ника на WhatsApp",
            "description": "Можно выбрать ник заранее",
            "application_url": None,
        },
        WHATSAPP_NICKNAME_NEWS,
    )
    assert invalid is True
    assert reason == "product_feature_news"


def test_startup_battle_refined_to_hackathon():
    refined = refine_opportunity_type(STARTUP_BATTLE, "конкурс")
    assert refined == "хакатон"
    assert is_startup_pitch_competition(STARTUP_BATTLE) is True


def test_startup_battle_tags_not_contest():
    tags = build_opportunity_tags(
        STARTUP_BATTLE,
        title="STARTUP BATTLE на 500к₸ от LaunchZone",
        description="Для школьников и студентов",
        primary_type="хакатон",
    )
    assert "конкурс" not in tags
    assert tags[0] == "стартапы"
    assert "хакатон" in tags


def test_real_essay_contest_stays_contest():
    refined = refine_opportunity_type(REAL_ESSAY_CONTEST, "эссе")
    assert refined == "эссе"
    assert is_startup_pitch_competition(REAL_ESSAY_CONTEST) is False

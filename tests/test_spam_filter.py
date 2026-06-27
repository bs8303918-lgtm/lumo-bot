"""Tests for consulting / success-story spam filter."""

from llm.spam_filter import is_likely_consulting_promo, is_likely_spam_or_ad

CONSULTING_POST = """
100% ГРАНТ В США 😭 🇺🇸

Narkes получила полный грант от программы BOLASHAK на обучение в Northeastern University.
Два года документов, эссе, интервью и нервов.

Её историю и отзыв можете прочитать здесь.

Если вы тоже хотите выиграть гранты на DAAD, GKS, Stipendium Hungaricum,
Chevening, Fulbright или Bolashak — запишитесь на консультацию.

WhatsApp для записи на бакалавриат и магистратуру 2027-2028 уже открыт.
"""

REAL_GRANT = """
Открыт набор на стипендию DAAD для магистратуры в Германии.
Дедлайн: 15.10.2026
Подать заявку: https://daad.de/apply
Требования: IELTS 6.5, мотивационное письмо.
"""


def test_consulting_success_story_is_spam():
    is_spam, reason = is_likely_consulting_promo(CONSULTING_POST)
    assert is_spam is True
    assert reason is not None


def test_consulting_post_skipped_before_llm():
    is_spam, reason = is_likely_spam_or_ad(CONSULTING_POST)
    assert is_spam is True


def test_real_daad_announcement_not_consulting_spam():
    is_spam, _ = is_likely_consulting_promo(REAL_GRANT)
    assert is_spam is False

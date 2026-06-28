"""Категоризация интереса: локально → LLM один раз если слабо → матчинг без LLM."""

from __future__ import annotations

import json
import logging
import time

from config import get_settings
from llm.client import LLMClient
from services.interest_admin_review import get_approved_domains
from services.interest_matcher import OPPORTUNITY_TYPES, is_standard_category
from services.interest_profile import InterestProfile, apply_interest_defaults, parse_interest_profile

logger = logging.getLogger(__name__)

_approved_domains_cache: tuple[float, list[str]] | None = None
_APPROVED_DOMAINS_TTL_SEC = 300.0


async def _approved_domains_cached() -> list[str]:
    global _approved_domains_cache
    now = time.monotonic()
    if _approved_domains_cache and now - _approved_domains_cache[0] < _APPROVED_DOMAINS_TTL_SEC:
        return _approved_domains_cache[1]
    domains = await get_approved_domains()
    _approved_domains_cache = (now, domains)
    return domains


def _needs_llm_categorization(profile: InterestProfile) -> bool:
    """LLM если мало типов или профиль размытый."""
    if len(profile.types) >= 2:
        return False
    if profile.admin_questions:
        return True
    if not profile.types and len(profile.all_categories()) < 2:
        return True
    if len(profile.types) < 2 and len(profile.all_categories()) < 2:
        return True
    return False


def _merge_llm_types(profile: InterestProfile, llm_categories: list[str]) -> None:
    for raw in llm_categories:
        norm = raw.lower().strip().replace(" ", "_")
        if norm not in OPPORTUNITY_TYPES:
            continue
        if norm not in profile.types:
            profile.types.append(norm)


async def categorize_interest(
    interest_query: str,
    *,
    user_id: int | None = None,
    approved_domains: list[str] | None = None,
    skip_llm: bool = False,
) -> tuple[InterestProfile, str]:
    """
    Разобрать интерес школьника.
    Returns: (profile, source) где source = local | llm | hybrid
    """
    text = (interest_query or "").strip()
    approved = approved_domains if approved_domains is not None else await _approved_domains_cached()
    profile = parse_interest_profile(text, approved_domains=approved, apply_defaults=False)
    source = "local"

    settings = get_settings()
    if (
        not skip_llm
        and settings.llm_interest_categorization
        and settings.llm_user_configured
        and _needs_llm_categorization(profile)
    ):
        try:
            llm_cats, _raw = await LLMClient().extract_interest_categories(text)
            if llm_cats:
                had_types = bool(profile.types)
                _merge_llm_types(profile, llm_cats)
                if profile.types:
                    source = "hybrid" if had_types else "llm"
                logger.info(
                    "Interest LLM categories user_id=%s source=%s cats=%s",
                    user_id,
                    source,
                    profile.types,
                )
        except Exception as exc:
            logger.warning("Interest LLM categorization failed: %s", exc)

    apply_interest_defaults(profile, text)

    return profile, source


def categories_from_json(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x).lower().strip() for x in data if x]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


async def get_or_categorize_user_interest(
    user_id: int,
    interest_query: str,
    *,
    stored_query: str | None = None,
    stored_categories_json: str | None = None,
) -> tuple[InterestProfile, list[str], str]:
    """
    Взять категории из БД если интерес не менялся, иначе categorize_interest.
    """
    text = interest_query.strip()
    if (
        stored_categories_json
        and stored_query
        and stored_query.strip() == text
    ):
        cats = categories_from_json(stored_categories_json)
        if cats:
            approved = await get_approved_domains()
            profile = parse_interest_profile(text, approved_domains=approved)
            profile.types = [c for c in cats if is_standard_category(c)]
            profile.domains = [c for c in cats if c not in profile.types]
            return profile, cats, "cached"

    profile, source = await categorize_interest(text, user_id=user_id)
    return profile, profile.all_categories(), source

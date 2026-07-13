import asyncio
import json
import logging
import re
import time

import httpx
from google import genai
from google.genai import types

from config import get_settings
from llm.deadline import format_today
from llm.json_utils import coerce_llm_dict
from llm.prompts import (
    CATALOG_MATCH_PROMPT,
    CLASSIFICATION_PROMPT,
    INTEREST_CATEGORIES_PROMPT,
    RELEVANCE_PROMPT,
    TEAM_PROFILE_PROMPT,
)
from logging_setup import log_error
from services.team_catalog import skills_catalog_for_prompt

logger = logging.getLogger(__name__)

_semaphore: asyncio.Semaphore | None = None
_user_semaphore: asyncio.Semaphore | None = None
_rate_lock = asyncio.Lock()
_user_rate_lock = asyncio.Lock()
_last_request_at: float = 0.0
_last_user_request_at: float = 0.0


def get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(get_settings().llm_max_concurrent)
    return _semaphore


def get_user_semaphore() -> asyncio.Semaphore:
    global _user_semaphore
    if _user_semaphore is None:
        _user_semaphore = asyncio.Semaphore(get_settings().llm_user_max_concurrent)
    return _user_semaphore


async def _wait_rate_limit(*, user: bool = False) -> None:
    """Catalog/monitor LLM — медленнее. user=True — отдельная очередь для интересов."""
    global _last_request_at, _last_user_request_at
    settings = get_settings()
    if user:
        min_gap = settings.llm_user_request_delay_seconds
        lock = _user_rate_lock
        state = "_last_user_request_at"
    else:
        min_gap = settings.llm_request_delay_seconds
        lock = _rate_lock
        state = "_last_request_at"
    async with lock:
        last = _last_user_request_at if user else _last_request_at
        elapsed = time.monotonic() - last
        if elapsed < min_gap:
            await asyncio.sleep(min_gap - elapsed)
        if user:
            _last_user_request_at = time.monotonic()
        else:
            _last_request_at = time.monotonic()


def _extract_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _normalize_json_object(data) -> dict | None:
    return coerce_llm_dict(data)


def _is_quota_error(exc: Exception) -> bool:
    msg = str(exc).upper()
    return (
        "429" in msg
        or "RESOURCE_EXHAUSTED" in msg
        or "QUOTA" in msg
        or "RATE_LIMIT" in msg
        or "RATE LIMIT" in msg
    )


def _is_transient_network_error(exc: Exception) -> bool:
    if isinstance(
        exc,
        (
            httpx.ConnectError,
            httpx.TimeoutException,
            httpx.ReadTimeout,
            httpx.ConnectTimeout,
            httpx.WriteTimeout,
            httpx.PoolTimeout,
            httpx.NetworkError,
        ),
    ):
        return True
    cause = exc.__cause__
    return isinstance(cause, httpx.NetworkError) if cause else False


def _network_retry_delay(attempt: int) -> float:
    return min(get_settings().llm_429_retry_base_seconds * (attempt + 1), 10.0)


def _log_llm_failure(exc: Exception, *, health_cache) -> None:
    if _is_quota_error(exc):
        logger.warning("Groq лимит — запрос отложен на следующий цикл")
        health_cache(False)
    elif _is_transient_network_error(exc):
        logger.warning("LLM: ошибка сети (%s) — повторим позже", type(exc).__name__)
        health_cache(False)
    else:
        log_error(logger, "llm_client", exc)
        health_cache(False)


def _retry_after_seconds(response: httpx.Response, attempt: int) -> float:
    raw = response.headers.get("retry-after") or response.headers.get("Retry-After")
    if raw:
        try:
            return max(float(raw), 1.0)
        except ValueError:
            pass
    settings = get_settings()
    return settings.llm_429_retry_base_seconds * (attempt + 1)


class LLMClient:
    _http_client: httpx.AsyncClient | None = None

    @classmethod
    async def close_http(cls) -> None:
        if cls._http_client is not None and not cls._http_client.is_closed:
            await cls._http_client.aclose()
        cls._http_client = None

    def _http_client_instance(self) -> httpx.AsyncClient:
        if LLMClient._http_client is None or LLMClient._http_client.is_closed:
            settings = get_settings()
            LLMClient._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=15.0, read=60.0, write=30.0, pool=10.0),
                limits=httpx.Limits(max_connections=4, max_keepalive_connections=2),
            )
        return LLMClient._http_client

    def __init__(self):
        self.settings = get_settings()
        self._gemini_client: genai.Client | None = None
        self._health_checked_at: float = 0.0
        self._health_ok: bool = False

    @property
    def _uses_openai(self) -> bool:
        return self.settings.llm_provider.lower() == "openai"

    def _gemini(self) -> genai.Client:
        if self._gemini_client is None:
            self._gemini_client = genai.Client(api_key=self.settings.gemini_api_key)
        return self._gemini_client

    def _health_ttl(self) -> int:
        if self._health_ok:
            return self.settings.llm_health_check_interval_seconds
        return self.settings.llm_health_fail_cache_seconds

    def _cache_health(self, ok: bool) -> None:
        self._health_checked_at = time.monotonic()
        self._health_ok = ok

    async def is_available(self) -> bool:
        if not self.settings.llm_configured:
            return False
        age = time.monotonic() - self._health_checked_at
        if self._health_checked_at and age < self._health_ttl():
            return self._health_ok
        ok = await self._run_health_check()
        self._cache_health(ok)
        return ok

    async def check_relevance(self, interest_query: str, message_text: str) -> tuple[dict | None, str | None]:
        prompt = RELEVANCE_PROMPT.format(
            interest_query=interest_query,
            message_text=message_text,
            today=format_today(),
        )
        raw: str | None = None
        async with get_semaphore():
            try:
                await _wait_rate_limit()
                if self._uses_openai:
                    raw = await self._openai_generate(prompt, max_tokens=1024)
                else:
                    raw = await self._gemini_generate(prompt, max_tokens=1024)
                data = _normalize_json_object(_extract_json(raw))
                self._cache_health(data is not None)
                return data, raw
            except json.JSONDecodeError as exc:
                log_error(logger, "llm_client", exc, {"raw_response": raw})
                return None, raw
            except Exception as exc:
                _log_llm_failure(exc, health_cache=self._cache_health)
                return None, raw

    async def classify_opportunity(self, message_text: str) -> tuple[dict | None, str | None]:
        prompt = CLASSIFICATION_PROMPT.format(message_text=message_text, today=format_today())
        return await self._json_prompt(prompt, max_tokens=1536)

    async def extract_interest_categories(
        self, interest_query: str
    ) -> tuple[list[str], list[str], str | None]:
        prompt = INTEREST_CATEGORIES_PROMPT.format(interest_query=interest_query)
        data, raw = await self._json_prompt(prompt, max_tokens=256, user_profile=True)
        if not data:
            return [], [], raw
        categories = data.get("categories") or []
        domains = data.get("domains") or []
        cats_out: list[str] = []
        if isinstance(categories, list):
            cats_out = [str(c).lower().strip() for c in categories if c]
        domains_out: list[str] = []
        if isinstance(domains, list):
            domains_out = [str(d).lower().strip().replace(" ", "_") for d in domains if d]
        return cats_out, domains_out, raw

    async def extract_team_profile(self, team_prompt: str) -> tuple[dict | None, str | None]:
        prompt = TEAM_PROFILE_PROMPT.format(
            team_prompt=team_prompt,
            skills_catalog=skills_catalog_for_prompt(),
        )
        return await self._json_prompt(prompt, max_tokens=384, user_profile=True)

    async def match_catalog_items(
        self,
        interest_query: str,
        items: list[dict],
        max_pick: int = 5,
    ) -> tuple[list[int], str | None]:
        if not items:
            return [], None
        lines = []
        for item in items:
            lines.append(
                f"- id={item['id']} | {item['type']} | {item['title']} | {item['description'][:120]}"
            )
        prompt = CATALOG_MATCH_PROMPT.format(
            interest_query=interest_query,
            catalog_list="\n".join(lines),
            max_pick=max_pick,
        )
        data, raw = await self._json_prompt(prompt, max_tokens=512)
        if not data:
            return [], raw
        ids = data.get("relevant_ids") or []
        if isinstance(ids, list):
            return [int(x) for x in ids if str(x).isdigit()], raw
        return [], raw

    async def _json_prompt(
        self,
        prompt: str,
        max_tokens: int,
        *,
        user_profile: bool = False,
    ) -> tuple[dict | None, str | None]:
        raw: str | None = None
        sem = get_user_semaphore() if user_profile else get_semaphore()
        async with sem:
            try:
                await _wait_rate_limit(user=user_profile)
                if self._uses_openai:
                    raw = await self._openai_generate(
                        prompt,
                        max_tokens=max_tokens,
                        user_profile=user_profile,
                    )
                else:
                    raw = await self._gemini_generate(prompt, max_tokens=max_tokens)
                data = _normalize_json_object(_extract_json(raw))
                if data is None and raw:
                    logger.warning("LLM вернул не объект JSON — пропускаем ответ")
                self._cache_health(data is not None)
                return data, raw
            except json.JSONDecodeError as exc:
                log_error(logger, "llm_client", exc, {"raw_response": raw})
                return None, raw
            except Exception as exc:
                _log_llm_failure(exc, health_cache=self._cache_health)
                return None, raw

    async def health_check(self) -> bool:
        """Force a live API ping (e.g. /health command)."""
        if not self.settings.llm_configured:
            return False
        ok = await self._run_health_check()
        self._cache_health(ok)
        return ok

    async def _run_health_check(self) -> bool:
        try:
            await _wait_rate_limit()
            if self._uses_openai:
                text = await self._openai_generate("ping", max_tokens=5, json_mode=False)
            else:
                text = await self._gemini_generate("ping", max_tokens=5)
            return bool(text and text.strip())
        except Exception as exc:
            if _is_quota_error(exc):
                logger.warning(
                    "LLM health: временный лимит (%s)",
                    self.settings.llm_model_name,
                )
            elif _is_transient_network_error(exc):
                logger.warning("LLM health: сеть недоступна (%s)", type(exc).__name__)
            else:
                log_error(logger, "llm_client", exc, {"check": "health"})
            return False

    async def _gemini_generate(self, prompt: str, max_tokens: int) -> str:
        response = await asyncio.to_thread(
            self._gemini().models.generate_content,
            model=self.settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                max_output_tokens=max_tokens,
                temperature=0.2,
            ),
        )
        return response.text or ""

    async def _openai_generate(
        self,
        prompt: str,
        max_tokens: int,
        json_mode: bool = True,
        *,
        user_profile: bool = False,
    ) -> str:
        url = f"{self.settings.openai_base_url.rstrip('/')}/chat/completions"
        api_key = (
            self.settings.openai_user_api_key_effective
            if user_profile
            else self.settings.openai_api_key
        )
        payload: dict = {
            "model": self.settings.openai_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        max_retries = self.settings.llm_429_max_retries
        client = self._http_client_instance()
        for attempt in range(max_retries + 1):
            try:
                response = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            except httpx.HTTPError as exc:
                if _is_transient_network_error(exc) and attempt < max_retries:
                    wait = _network_retry_delay(attempt)
                    logger.warning(
                        "LLM сеть (%s) — пауза %.0f сек, повтор %d/%d",
                        type(exc).__name__,
                        wait,
                        attempt + 1,
                        max_retries,
                    )
                    await asyncio.sleep(wait)
                    await _wait_rate_limit()
                    continue
                raise

            if response.status_code == 429:
                if attempt >= max_retries:
                    raise RuntimeError(f"429 rate limit: {response.text[:300]}")
                wait = _retry_after_seconds(response, attempt)
                logger.info(
                    "Groq 429 — пауза %.0f сек, повтор %d/%d",
                    wait,
                    attempt + 1,
                    max_retries,
                )
                await asyncio.sleep(wait)
                await _wait_rate_limit()
                continue
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"] or ""
        raise RuntimeError("LLM request failed after retries")

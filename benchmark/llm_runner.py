"""Run unified matching benchmark through multiple LLM providers."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

import httpx
from google import genai
from google.genai import types

from llm.deadline import format_today
from llm.json_utils import coerce_llm_dict

from benchmark.compare import compare_matching, normalize_prediction
from benchmark.prompts import UNIFIED_MATCHING_PROMPT
from benchmark.schema import CompareResult, GoldenUserProfile, ModelConfig, PostRecord

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


class BenchmarkLLMRunner:
    def __init__(self, *, request_delay: float = 1.0, max_concurrent: int = 2):
        self.request_delay = request_delay
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._last_request_at = 0.0
        self._lock = asyncio.Lock()
        self._http: httpx.AsyncClient | None = None
        self._gemini_clients: dict[str, genai.Client] = {}

    async def close(self) -> None:
        if self._http and not self._http.is_closed:
            await self._http.aclose()
        self._http = None

    def _http_client(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=15.0, read=90.0, write=30.0, pool=10.0),
                limits=httpx.Limits(max_connections=4, max_keepalive_connections=2),
            )
        return self._http

    async def _throttle(self) -> None:
        async with self._lock:
            elapsed = asyncio.get_event_loop().time() - self._last_request_at
            if elapsed < self.request_delay:
                await asyncio.sleep(self.request_delay - elapsed)
            self._last_request_at = asyncio.get_event_loop().time()

    async def match_post(
        self,
        model: ModelConfig,
        *,
        user_profile: str,
        message_text: str,
        profile_id: str = "default",
        profile_label: str = "default",
    ) -> tuple[dict | None, str | None, str | None]:
        prompt = UNIFIED_MATCHING_PROMPT.format(
            user_profile=user_profile,
            message_text=message_text,
            today=format_today(),
        )
        raw: str | None = None
        async with self._semaphore:
            await self._throttle()
            try:
                if model.provider == "gemini":
                    raw = await self._gemini_generate(model, prompt)
                elif model.provider == "anthropic":
                    raw = await self._anthropic_generate(model, prompt)
                else:
                    raw = await self._openai_compatible_generate(model, prompt)
                data = normalize_prediction(coerce_llm_dict(_extract_json(raw)))
                if data is not None:
                    data["_profile_id"] = profile_id
                    data["_profile_label"] = profile_label
                return data, raw, None
            except json.JSONDecodeError as exc:
                return None, raw, f"JSON decode: {exc}"
            except Exception as exc:
                logger.warning("Benchmark LLM %s failed: %s", model.name, exc)
                return None, raw, str(exc)

    async def _openai_compatible_generate(self, model: ModelConfig, prompt: str) -> str:
        base = (model.base_url or "https://api.openai.com/v1").rstrip("/")
        url = f"{base}/chat/completions"
        payload = {
            "model": model.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 1536,
            "response_format": {"type": "json_object"},
        }
        response = await self._http_client().post(
            url,
            headers={
                "Authorization": f"Bearer {model.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"] or ""

    async def _anthropic_generate(self, model: ModelConfig, prompt: str) -> str:
        url = "https://api.anthropic.com/v1/messages"
        payload = {
            "model": model.model,
            "max_tokens": 1536,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": prompt}],
        }
        response = await self._http_client().post(
            url,
            headers={
                "x-api-key": model.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        parts = data.get("content") or []
        texts = [p.get("text", "") for p in parts if isinstance(p, dict) and p.get("type") == "text"]
        return "".join(texts)

    async def _gemini_generate(self, model: ModelConfig, prompt: str) -> str:
        client = self._gemini_clients.get(model.api_key)
        if client is None:
            client = genai.Client(api_key=model.api_key)
            self._gemini_clients[model.api_key] = client
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=model.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                max_output_tokens=1536,
                temperature=0.2,
            ),
        )
        return response.text or ""


async def run_matching_benchmark(
    posts: list[PostRecord],
    models: list[ModelConfig],
    profile: GoldenUserProfile,
    *,
    request_delay: float = 1.0,
    max_concurrent: int = 2,
    compare_golden: bool = True,
) -> list[CompareResult]:
    runner = BenchmarkLLMRunner(request_delay=request_delay, max_concurrent=max_concurrent)
    results: list[CompareResult] = []
    try:
        for model in models:
            for post in posts:
                predicted, raw, parse_error = await runner.match_post(
                    model,
                    user_profile=profile.interest_query,
                    message_text=post.message_text,
                    profile_id=profile.id,
                    profile_label=profile.name or profile.id,
                )
                if compare_golden and post.golden is not None:
                    compared = compare_matching(
                        record_id=post.id,
                        model=model.name,
                        golden=post.golden,
                        predicted=predicted,
                        raw_response=raw,
                        parse_error=parse_error,
                    )
                else:
                    compared = CompareResult(
                        record_id=post.id,
                        model=model.name,
                        predicted=predicted or {},
                        raw_response=raw,
                        parse_error=parse_error,
                    )
                results.append(compared)
    finally:
        await runner.close()
    return results


# Backward-compatible alias
run_benchmark = run_matching_benchmark

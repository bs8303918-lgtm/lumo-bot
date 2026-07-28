"""Fetch public web pages and extract readable text for LLM classification."""

from __future__ import annotations

import logging
import re
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

_SKIP_HOST_SUFFIXES = (
    "t.me",
    "telegram.me",
    "telegram.org",
    "instagram.com",
    "cdninstagram.com",
    "facebook.com",
    "fb.com",
    "fb.me",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "linkedin.com",
    "youtube.com",
    "youtu.be",
)

_SKIP_HOST_EXACT = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "example.com",
        "example.org",
    }
)

_DEFAULT_UA = (
    "Mozilla/5.0 (compatible; LumoBot/1.0; +https://t.me/LumoAI1bot) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_WS_RE = re.compile(r"[ \t]+")
_BLANK_RE = re.compile(r"\n{3,}")


class _HTMLTextExtractor(HTMLParser):
    _SKIP_TAGS = frozenset(
        {"script", "style", "noscript", "svg", "iframe", "head", "nav", "footer", "aside"}
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in self._SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag.lower() in {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "section", "article"}:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag.lower() in {"p", "div", "li", "tr", "h1", "h2", "h3", "h4", "section", "article"}:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = data.strip()
        if text:
            self._parts.append(text + " ")

    def get_text(self) -> str:
        raw = "".join(self._parts)
        raw = _WS_RE.sub(" ", raw)
        raw = _BLANK_RE.sub("\n\n", raw)
        return raw.strip()


def html_to_text(html: str) -> str:
    parser = _HTMLTextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        # Broken HTML — still return whatever was parsed.
        pass
    return parser.get_text()


def is_fetchable_page_url(url: str | None) -> bool:
    if not url or not isinstance(url, str):
        return False
    text = url.strip()
    if not text.lower().startswith("http"):
        return False
    try:
        parsed = urlparse(text.split()[0])
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host or host in _SKIP_HOST_EXACT:
        return False
    if host.endswith(".local") or host.endswith(".internal"):
        return False
    for suffix in _SKIP_HOST_SUFFIXES:
        if host == suffix or host.endswith("." + suffix):
            return False
    # Block obvious private/link-local IPv4
    if host.startswith("10.") or host.startswith("192.168.") or host.startswith("169.254."):
        return False
    if re.match(r"^172\.(1[6-9]|2\d|3[0-1])\.", host):
        return False
    return True


async def fetch_page_text(
    url: str,
    *,
    timeout_seconds: float = 10.0,
    max_bytes: int = 1_500_000,
    max_chars: int = 8000,
    user_agent: str = _DEFAULT_UA,
) -> str | None:
    """Download a public page and return cleaned text, or None on failure."""
    if not is_fetchable_page_url(url):
        return None

    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
    }
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout_seconds,
            headers=headers,
        ) as client:
            async with client.stream("GET", url.strip()) as response:
                if response.status_code >= 400:
                    logger.info("page_fetch: HTTP %s for %s", response.status_code, url)
                    return None
                content_type = (response.headers.get("content-type") or "").lower()
                if content_type and "html" not in content_type and "text/" not in content_type:
                    logger.info("page_fetch: skip non-text content-type %s for %s", content_type, url)
                    return None

                chunks: list[bytes] = []
                total = 0
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        logger.info("page_fetch: truncated oversized body for %s", url)
                        break
                    chunks.append(chunk)
                raw = b"".join(chunks)
    except Exception as exc:
        logger.info("page_fetch: failed %s (%s)", url, type(exc).__name__)
        return None

    encoding = "utf-8"
    try:
        # charset from content-type is handled by httpx on .text; for stream we decode ourselves
        html = raw.decode(encoding, errors="replace")
    except Exception:
        return None

    text = html_to_text(html)
    if not text or len(text) < 40:
        return None
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + "…"
    return text


async def fetch_linked_page_text(
    *texts: str | None,
    timeout_seconds: float = 10.0,
    max_chars: int = 8000,
) -> tuple[str | None, str | None]:
    """Pick first non-Telegram URL from texts and fetch page text.

    Returns (url, page_text) or (None, None).
    """
    from services.opportunity_links import extract_registration_url

    url = extract_registration_url(*texts)
    if not url or not is_fetchable_page_url(url):
        return None, None
    page_text = await fetch_page_text(
        url,
        timeout_seconds=timeout_seconds,
        max_chars=max_chars,
    )
    if not page_text:
        return url, None
    return url, page_text

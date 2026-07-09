"""JSONL schemas for benchmark posts, user profile, and model configs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MatchingGolden:
    is_opportunity: bool = False
    category: str | None = None
    matches_profile: bool = False
    is_eligible: bool = False
    extracted_deadline: str | None = None
    key_benefits: list[str] = field(default_factory=list)
    matched_skills: list[str] = field(default_factory=list)
    red_flags: str | None = None
    title: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> MatchingGolden | None:
        if not data:
            return None
        if data.get("is_opportunity") is None and not any(
            data.get(k) for k in ("category", "matches_profile", "is_eligible")
        ):
            return None
        benefits = data.get("key_benefits") or []
        skills = data.get("matched_skills") or []
        return cls(
            is_opportunity=bool(data.get("is_opportunity")),
            category=_nullable_str(data.get("category")),
            matches_profile=bool(data.get("matches_profile")),
            is_eligible=bool(data.get("is_eligible")),
            extracted_deadline=_nullable_str(data.get("extracted_deadline")),
            key_benefits=[str(x) for x in benefits if x],
            matched_skills=[str(x) for x in skills if x],
            red_flags=_nullable_str(data.get("red_flags")),
            title=_nullable_str(data.get("title")),
        )


@dataclass
class PostRecord:
    """Raw Telegram post — необработанный текст из raw_messages."""

    id: str
    message_text: str
    message_link: str | None = None
    raw_message_id: int | None = None
    source_channel: str | None = None
    posted_at: str | None = None
    golden: MatchingGolden | None = None
    notes: str | None = None

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> PostRecord:
        record_id = str(row.get("id") or row.get("raw_message_id") or "").strip()
        if not record_id:
            raise ValueError("post row must have 'id' or 'raw_message_id'")
        text = (row.get("message_text") or row.get("text") or "").strip()
        if not text:
            raise ValueError(f"post row {record_id!r} has empty message_text")
        golden_raw = row.get("golden") or row.get("expected")
        return cls(
            id=record_id,
            message_text=text,
            message_link=_nullable_str(row.get("message_link")),
            raw_message_id=row.get("raw_message_id"),
            source_channel=_nullable_str(row.get("source_channel")),
            posted_at=_nullable_str(row.get("posted_at")),
            golden=MatchingGolden.from_dict(golden_raw) if golden_raw else None,
            notes=_nullable_str(row.get("notes")),
        )


@dataclass
class GoldenUserProfile:
    id: str
    interest_query: str
    name: str | None = None
    expected_categories: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GoldenUserProfile:
        query = (data.get("interest_query") or "").strip()
        if not query:
            raise ValueError("golden user profile must have interest_query")
        return cls(
            id=str(data.get("id") or "golden_user"),
            interest_query=query,
            name=_nullable_str(data.get("name")),
            expected_categories=data.get("expected_categories") or {},
        )


@dataclass
class ModelConfig:
    name: str
    provider: str
    model: str
    api_key: str
    base_url: str | None = None
    api_key_env: str | None = None

    @classmethod
    def from_dict(cls, row: dict[str, Any], *, env_lookup) -> ModelConfig:
        name = str(row.get("name") or row.get("model") or "").strip()
        provider = str(row.get("provider") or "openai").strip().lower()
        model = str(row.get("model") or "").strip()
        if not name or not model:
            raise ValueError("model config needs 'name' and 'model'")
        api_key_env = (row.get("api_key_env") or "").strip() or None
        inline_key = (row.get("api_key") or "").strip()
        api_key = inline_key or (env_lookup(api_key_env) if api_key_env else "")
        if not api_key:
            hint = api_key_env or "api_key"
            raise ValueError(f"model {name!r}: missing API key ({hint})")
        return cls(
            name=name,
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=_nullable_str(row.get("base_url")),
            api_key_env=api_key_env,
        )


@dataclass
class FieldError:
    field: str
    category: str
    expected: Any = None
    actual: Any = None
    detail: str | None = None


@dataclass
class CompareResult:
    record_id: str
    model: str
    errors: list[FieldError] = field(default_factory=list)
    predicted: dict[str, Any] = field(default_factory=dict)
    raw_response: str | None = None
    parse_error: str | None = None

    @property
    def ok(self) -> bool:
        return not self.errors and not self.parse_error


def _nullable_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"null", "none", "—", "-", "n/a"}:
        return None
    return text


def load_posts_jsonl(path: Path) -> list[PostRecord]:
    records: list[PostRecord] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        row = json.loads(line)
        try:
            records.append(PostRecord.from_dict(row))
        except ValueError as exc:
            raise ValueError(f"{path}:{line_no}: {exc}") from exc
    return records


def load_user_profile(path: Path) -> GoldenUserProfile:
    data = json.loads(path.read_text(encoding="utf-8"))
    return GoldenUserProfile.from_dict(data)


def load_stage2_profiles(path: Path) -> list[GoldenUserProfile]:
    profiles: list[GoldenUserProfile] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        row = json.loads(line)
        query = (row.get("interest_query") or "").strip()
        if not query:
            raise ValueError(f"{path}:{line_no}: empty interest_query")
        label = row.get("cluster") or row.get("username") or row.get("id")
        profiles.append(
            GoldenUserProfile(
                id=str(row.get("id") or f"profile_{line_no}"),
                interest_query=query,
                name=f"{label} (@{row.get('username')})" if row.get("username") else str(label),
            )
        )
    return profiles


def load_model_configs(path: Path, *, env_lookup) -> list[ModelConfig]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data if isinstance(data, list) else data.get("models", [])
    return [ModelConfig.from_dict(row, env_lookup=env_lookup) for row in rows]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


# Backward-compatible aliases
GoldenRecord = PostRecord
load_golden_jsonl = load_posts_jsonl

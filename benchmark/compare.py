"""Compare LLM matching output with golden labels and compute inter-model agreement."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime
from difflib import SequenceMatcher
from typing import Any

from benchmark.schema import CompareResult, FieldError, MatchingGolden


def _norm(value: str | None) -> str:
    if not value:
        return ""
    text = str(value).lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[«»\"'`]", "", text)
    return text


def _norm_category(value: str | None) -> str:
    text = _norm(value).replace(" ", "_")
    aliases = {
        "не возможность": "не_возможность",
        "not_opportunity": "не_возможность",
        "summer_school": "летняя_школа",
        "internship": "стажировка",
        "hackathon": "хакатон",
    }
    return aliases.get(text, text)


def text_similarity(a: str | None, b: str | None) -> float:
    na, nb = _norm(a), _norm(b)
    if not na and not nb:
        return 1.0
    if not na or not nb:
        return 0.0
    if na in nb or nb in na:
        return 0.9
    return SequenceMatcher(None, na, nb).ratio()


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def deadlines_match(expected: str | None, actual: str | None) -> bool:
    exp = _parse_iso_date(expected)
    act = _parse_iso_date(actual)
    if exp and act:
        return exp == act
    if not expected and not actual:
        return True
    return text_similarity(expected, actual) >= 0.85


def list_overlap_score(expected: list[str], actual: list[str]) -> float:
    if not expected and not actual:
        return 1.0
    if not expected or not actual:
        return 0.0
    exp_norm = {_norm(x) for x in expected if _norm(x)}
    act_norm = {_norm(x) for x in actual if _norm(x)}
    if not exp_norm or not act_norm:
        return 0.0
    hits = 0
    for item in exp_norm:
        if any(item in a or a in item for a in act_norm):
            hits += 1
    return hits / max(len(exp_norm), 1)


def normalize_prediction(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    benefits = data.get("key_benefits") or []
    skills = data.get("matched_skills") or []
    return {
        "is_opportunity": bool(data.get("is_opportunity")),
        "title": data.get("title"),
        "category": _norm_category(data.get("category") or data.get("type")),
        "matches_profile": bool(data.get("matches_profile")),
        "is_eligible": bool(data.get("is_eligible")),
        "extracted_deadline": data.get("extracted_deadline"),
        "key_benefits": [str(x) for x in benefits if x] if isinstance(benefits, list) else [],
        "matched_skills": [str(x) for x in skills if x] if isinstance(skills, list) else [],
        "red_flags": data.get("red_flags"),
    }


def compare_matching(
    *,
    record_id: str,
    model: str,
    golden: MatchingGolden,
    predicted: dict[str, Any] | None,
    raw_response: str | None = None,
    parse_error: str | None = None,
) -> CompareResult:
    result = CompareResult(
        record_id=record_id,
        model=model,
        predicted=normalize_prediction(predicted),
        raw_response=raw_response,
        parse_error=parse_error,
    )
    if parse_error:
        result.errors.append(
            FieldError(field="_parse", category="json_parse_error", detail=parse_error)
        )
        return result
    if predicted is None:
        result.errors.append(
            FieldError(field="_parse", category="json_parse_error", detail="empty prediction")
        )
        return result

    pred = result.predicted

    if pred.get("is_opportunity") != golden.is_opportunity:
        cat = "false_positive" if pred.get("is_opportunity") else "false_negative"
        result.errors.append(
            FieldError(
                field="is_opportunity",
                category=cat,
                expected=golden.is_opportunity,
                actual=pred.get("is_opportunity"),
            )
        )

    if golden.category and _norm_category(pred.get("category")) != _norm_category(golden.category):
        result.errors.append(
            FieldError(
                field="category",
                category="wrong_category",
                expected=golden.category,
                actual=pred.get("category"),
            )
        )

    if pred.get("matches_profile") != golden.matches_profile:
        result.errors.append(
            FieldError(
                field="matches_profile",
                category="wrong_profile_match",
                expected=golden.matches_profile,
                actual=pred.get("matches_profile"),
            )
        )

    if pred.get("is_eligible") != golden.is_eligible:
        result.errors.append(
            FieldError(
                field="is_eligible",
                category="wrong_eligibility",
                expected=golden.is_eligible,
                actual=pred.get("is_eligible"),
            )
        )

    if golden.extracted_deadline and not deadlines_match(golden.extracted_deadline, pred.get("extracted_deadline")):
        result.errors.append(
            FieldError(
                field="extracted_deadline",
                category="wrong_deadline",
                expected=golden.extracted_deadline,
                actual=pred.get("extracted_deadline"),
            )
        )

    if golden.key_benefits and list_overlap_score(golden.key_benefits, pred.get("key_benefits") or []) < 0.4:
        result.errors.append(
            FieldError(
                field="key_benefits",
                category="missing_benefits" if not pred.get("key_benefits") else "wrong_benefits",
                expected=golden.key_benefits,
                actual=pred.get("key_benefits"),
            )
        )

    if golden.matched_skills and list_overlap_score(golden.matched_skills, pred.get("matched_skills") or []) < 0.4:
        result.errors.append(
            FieldError(
                field="matched_skills",
                category="missing_skills" if not pred.get("matched_skills") else "wrong_skills",
                expected=golden.matched_skills,
                actual=pred.get("matched_skills"),
            )
        )

    if golden.red_flags and text_similarity(golden.red_flags, pred.get("red_flags")) < 0.45:
        result.errors.append(
            FieldError(
                field="red_flags",
                category="missed_red_flags" if not pred.get("red_flags") else "wrong_red_flags",
                expected=golden.red_flags,
                actual=pred.get("red_flags"),
            )
        )

    return result


# Backward-compatible alias
compare_extraction = compare_matching


def summarize_errors(results: list[CompareResult]) -> dict[str, Any]:
    by_category: dict[str, int] = {}
    by_field: dict[str, int] = {}
    by_model: dict[str, dict[str, Any]] = {}
    total = len(results)
    ok = sum(1 for r in results if r.ok)

    for row in results:
        model_stats = by_model.setdefault(row.model, {"total": 0, "ok": 0, "errors": 0})
        model_stats["total"] += 1
        if row.ok:
            model_stats["ok"] += 1
        else:
            model_stats["errors"] += 1
        for err in row.errors:
            by_category[err.category] = by_category.get(err.category, 0) + 1
            by_field[err.field] = by_field.get(err.field, 0) + 1
            cats = model_stats.setdefault("categories", {})
            cats[err.category] = cats.get(err.category, 0) + 1

    return {
        "total_comparisons": total,
        "exact_match": ok,
        "exact_match_rate": round(ok / total, 4) if total else 0.0,
        "errors_by_category": dict(sorted(by_category.items(), key=lambda x: -x[1])),
        "errors_by_field": dict(sorted(by_field.items(), key=lambda x: -x[1])),
        "by_model": by_model,
    }


def summarize_model_agreement(results: list[CompareResult]) -> dict[str, Any]:
    """Согласие между моделями на одном посте (без golden)."""
    by_post: dict[str, list[CompareResult]] = defaultdict(list)
    for row in results:
        if row.parse_error:
            continue
        by_post[row.record_id].append(row)

    fields = (
        "is_opportunity",
        "category",
        "matches_profile",
        "is_eligible",
        "extracted_deadline",
    )
    field_agreement: dict[str, dict[str, int]] = {f: {"unanimous": 0, "split": 0} for f in fields}
    posts_with_multiple = 0

    for _post_id, rows in by_post.items():
        if len(rows) < 2:
            continue
        posts_with_multiple += 1
        for field in fields:
            values = []
            for row in rows:
                val = row.predicted.get(field)
                if field == "category":
                    val = _norm_category(val)
                values.append(val)
            if len(set(map(repr, values))) == 1:
                field_agreement[field]["unanimous"] += 1
            else:
                field_agreement[field]["split"] += 1

    return {
        "posts_with_multiple_models": posts_with_multiple,
        "field_agreement": field_agreement,
    }

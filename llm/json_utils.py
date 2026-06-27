def coerce_llm_dict(data) -> dict | None:
    """Groq иногда возвращает [{...}] вместо {...} — приводим к dict."""
    if data is None:
        return None
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                return item
    return None

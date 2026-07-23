from __future__ import annotations

from typing import Iterable


def conversion_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def score_lead(message: str = "", metadata: dict | None = None) -> dict:
    metadata = metadata or {}
    text = f"{message} {' '.join(str(value) for value in metadata.values())}".lower()
    urgency_words = ["today", "now", "urgent", "asap", "book", "quote", "price", "call"]
    buying_words = ["buy", "subscribe", "hire", "schedule", "appointment", "demo", "order"]

    urgency_score = min(5, sum(1 for word in urgency_words if word in text))
    buying_score = sum(1 for word in buying_words if word in text)
    buying_probability = min(100, 20 + urgency_score * 10 + buying_score * 15)
    has_contact = any(key in metadata for key in ("email", "phone", "contact"))
    if not has_contact:
        import re
        has_email = "@" in text
        has_phone = bool(re.search(r"\+?\d[\d\s().-]{7,}\d", text))
        has_contact = has_email or has_phone

    if has_contact:
        buying_probability = min(100, buying_probability + 15)

    if buying_probability >= 70 or urgency_score >= 4:
        status = "HOT"
    elif buying_probability >= 40 or urgency_score >= 2:
        status = "WARM"
    else:
        status = "COLD"

    return {
        "buying_probability": buying_probability,
        "urgency_score": urgency_score,
        "status": status,
    }


def top_sources(leads: Iterable) -> dict[str, int]:
    sources: dict[str, int] = {}
    for lead in leads:
        source = getattr(lead, "source", None) or "unknown"
        sources[source] = sources.get(source, 0) + 1
    return sources

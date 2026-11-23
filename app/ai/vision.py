"""Validate vision suggestions and keep provider details out of route code."""

import math
import os

from flask import current_app

from app.models.product import CATEGORIES


MINIMUM_CONFIDENCE = 0.65
PROVIDER_LABELS = {"gemini": "Google Gemini", "openai": "OpenAI"}
PROVIDER_KEYS = {"gemini": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY"}
EXPECTED_KEYS = {
    "title", "category", "title_confidence", "category_confidence",
    "abstain_reason",
}


class InvalidVisionResult(ValueError):
    """The provider returned data outside Market Mirror's small contract."""


def _valid_confidence(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and 0 <= value <= 1)


def validate_vision_result(raw):
    """Treat model output as untrusted input and return a UI-safe result."""
    if not isinstance(raw, dict) or set(raw) != EXPECTED_KEYS:
        raise InvalidVisionResult("Vision result has an unexpected shape.")

    title = raw["title"]
    category = raw["category"]
    reason = raw["abstain_reason"]
    if (not isinstance(title, str) or title != title.strip() or
            not 3 <= len(title) <= 80 or any(ord(character) < 32 for character in title)
            or "<" in title or ">" in title):
        raise InvalidVisionResult("Vision title is invalid.")
    if category not in CATEGORIES:
        raise InvalidVisionResult("Vision category is invalid.")
    if (not isinstance(reason, str) or len(reason) > 160 or
            any(ord(character) < 32 for character in reason)):
        raise InvalidVisionResult("Vision abstention reason is invalid.")
    if not _valid_confidence(raw["title_confidence"]) or not _valid_confidence(raw["category_confidence"]):
        raise InvalidVisionResult("Vision confidence is invalid.")

    suggested_title = title if raw["title_confidence"] >= MINIMUM_CONFIDENCE else None
    suggested_category = category if raw["category_confidence"] >= MINIMUM_CONFIDENCE else None
    suggestion = ({"title": suggested_title, "category": suggested_category}
                  if suggested_title or suggested_category else None)
    return {
        "suggestion": suggestion,
        "confidence": {
            "title": raw["title_confidence"],
            "category": raw["category_confidence"],
        },
        "abstain_reason": reason,
    }


def vision_available():
    """Report whether the optional feature can really answer a request."""
    if not current_app.config.get("VISION_AI_ENABLED", False):
        return False
    if callable(current_app.config.get("VISION_AI_ANALYZER")):
        return True
    provider = current_app.config.get("VISION_AI_PROVIDER")
    key_name = PROVIDER_KEYS.get(provider)
    return bool(key_name and os.environ.get(key_name, "").strip())


def vision_provider_label():
    """Return only a fixed display label, never raw environment text."""
    return PROVIDER_LABELS.get(current_app.config.get("VISION_AI_PROVIDER"), "AI provider")


def build_vision_provider():
    provider = current_app.config.get("VISION_AI_PROVIDER")
    arguments = {
        "model": current_app.config["VISION_AI_MODEL"],
        "timeout": current_app.config["VISION_AI_TIMEOUT_SECONDS"],
    }
    if provider == "gemini":
        from app.ai.gemini_vision import GeminiVisionProvider
        return GeminiVisionProvider(**arguments)
    if provider == "openai":
        from app.ai.openai_vision import OpenAIVisionProvider
        return OpenAIVisionProvider(**arguments)
    raise RuntimeError("Vision provider is unavailable.")


def analyze_listing_image(clean_jpeg):
    analyzer = current_app.config.get("VISION_AI_ANALYZER")
    if callable(analyzer):
        raw = analyzer(clean_jpeg)
    else:
        raw = build_vision_provider().analyze(clean_jpeg)
    return validate_vision_result(raw)

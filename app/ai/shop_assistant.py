"""Validate and orchestrate the read-only MM-027 shop assistant."""

import os

from flask import current_app, url_for
from sqlalchemy import select

from app.extensions import db
from app.images import image_exists
from app.models import Product
from app.models.product import CONDITIONS
from app.ai.shop_catalogue import select_shop_catalogue


class InvalidShopRequest(ValueError):
    """The browser request is outside the small assistant contract."""


class InvalidShopResult(ValueError):
    """The provider result is outside the trusted assistant contract."""


def _has_control(value):
    return any(ord(character) < 32 or 127 <= ord(character) <= 159
               for character in value)


def _request_text(value, minimum, maximum):
    if not isinstance(value, str):
        raise InvalidShopRequest("Assistant text must be a string.")
    cleaned = value.strip()
    if not minimum <= len(cleaned) <= maximum or _has_control(cleaned):
        raise InvalidShopRequest("Assistant text is outside the allowed length or format.")
    return cleaned


def validate_shop_request(payload):
    if not isinstance(payload, dict) or set(payload) != {"query", "history"}:
        raise InvalidShopRequest("Send one question and bounded history.")
    query = _request_text(payload["query"], 1, 300)
    history = payload["history"]
    if not isinstance(history, list) or len(history) > 6 or len(history) % 2:
        raise InvalidShopRequest("History must contain complete recent exchanges.")
    cleaned = []
    total = 0
    for index, message in enumerate(history):
        if not isinstance(message, dict) or set(message) != {"role", "content"}:
            raise InvalidShopRequest("History messages have an invalid shape.")
        expected_role = "user" if index % 2 == 0 else "assistant"
        if message["role"] != expected_role:
            raise InvalidShopRequest("History roles must alternate.")
        content = _request_text(message["content"], 1, 600)
        total += len(content)
        if total > 2400:
            raise InvalidShopRequest("History is too long.")
        cleaned.append({"role": expected_role, "content": content})
    return query, cleaned


def _result_text(value, minimum, maximum):
    if (not isinstance(value, str) or value != value.strip() or
            not minimum <= len(value) <= maximum or _has_control(value) or
            "<" in value or ">" in value):
        raise InvalidShopResult("Assistant output contains invalid text.")
    return value


def validate_shop_result(raw, allowed_ids):
    if (not isinstance(raw, dict) or
            set(raw) != {"summary", "recommendations", "follow_up"}):
        raise InvalidShopResult("Assistant output has an unexpected shape.")
    summary = _result_text(raw["summary"], 1, 500)
    follow_up = _result_text(raw["follow_up"], 0, 200)
    recommendations = raw["recommendations"]
    if not isinstance(recommendations, list) or len(recommendations) > 3:
        raise InvalidShopResult("Assistant recommendations are invalid.")
    allowed_ids = set(allowed_ids)
    seen = set()
    cleaned = []
    for item in recommendations:
        if not isinstance(item, dict) or set(item) != {"product_id", "reason"}:
            raise InvalidShopResult("Assistant recommendation has an invalid shape.")
        identifier = item["product_id"]
        if (type(identifier) is not int or identifier not in allowed_ids or
                identifier in seen):
            raise InvalidShopResult("Assistant recommended an untrusted product.")
        seen.add(identifier)
        cleaned.append({
            "product_id": identifier,
            "reason": _result_text(item["reason"], 1, 240),
        })
    return {"summary": summary, "recommendations": cleaned,
            "follow_up": follow_up}


def shop_assistant_available():
    if not current_app.config.get("SHOP_ASSISTANT_ENABLED", False):
        return False
    if callable(current_app.config.get("SHOP_ASSISTANT_GENERATOR")):
        return True
    return bool(os.environ.get("GEMINI_API_KEY", "").strip())


def _provider_result(query, history, catalogue, truncated):
    generator = current_app.config.get("SHOP_ASSISTANT_GENERATOR")
    if callable(generator):
        return generator(query, history, catalogue, truncated)
    from app.ai.gemini_shop import GeminiShopProvider
    provider = GeminiShopProvider(
        model=current_app.config["SHOP_ASSISTANT_MODEL"],
        timeout=current_app.config["SHOP_ASSISTANT_TIMEOUT_SECONDS"],
    )
    return provider.recommend(query, history, catalogue, truncated)


def _empty_answer(summary):
    return {
        "summary": summary,
        "recommendations": [],
        "follow_up": "Try the Explore page to browse and filter products manually.",
        "truncated": False,
        "explore_url": url_for("market.browse"),
    }


def answer_shop_query(query, history):
    catalogue, truncated = select_shop_catalogue(query)
    if not catalogue:
        return _empty_answer("There are no active products to recommend right now.")

    raw = _provider_result(query, history, catalogue, truncated)
    validated = validate_shop_result(raw, {item["id"] for item in catalogue})
    requested_ids = [item["product_id"] for item in validated["recommendations"]]
    products = []
    if requested_ids:
        products = db.session.scalars(select(Product).where(
            Product.id.in_(requested_ids), Product.status == "active"
        )).all()
    by_id = {product.id: product for product in products}
    reason_by_id = {item["product_id"]: item["reason"]
                    for item in validated["recommendations"]}
    hydrated = []
    for identifier in requested_ids:
        product = by_id.get(identifier)
        if product is None:
            continue
        cover = product.image_filename
        hydrated.append({
            "id": product.id,
            "title": product.title,
            "price": format(product.price, ".2f"),
            "currency": product.currency,
            "condition": CONDITIONS[product.condition],
            "url": url_for("market.detail", product_id=product.id),
            "image_url": (url_for("market.media", filename=cover)
                          if cover and image_exists(cover) else None),
            "reason": reason_by_id[identifier],
        })

    summary = validated["summary"]
    follow_up = validated["follow_up"]
    if requested_ids and not hydrated:
        summary = "Those suggestions are no longer available as active listings."
        follow_up = "Try the Explore page for the latest active products."
    elif len(hydrated) != len(requested_ids):
        summary = "Some suggestions changed availability; these active matches remain."
    return {
        "summary": summary,
        "recommendations": hydrated,
        "follow_up": follow_up,
        "truncated": truncated,
        "explore_url": url_for("market.browse"),
    }

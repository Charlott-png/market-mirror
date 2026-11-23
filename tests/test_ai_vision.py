"""MM-023 contracts written before AI vision implementation."""

from io import BytesIO
import json
import math
import os
from pathlib import Path
import re

import pytest
from PIL import Image, ImageOps
from sqlalchemy import func, select

from tests.test_marketplace import sign_in
from tests.test_seller_profile import Page


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_CATEGORIES = {
    "electronics", "home_garden", "clothing", "books_media",
    "sports_outdoors", "toys_games", "other",
}


def picture(size=(1600, 900), image_format="PNG", color=(40, 100, 160, 190)):
    stream = BytesIO()
    mode = "RGBA" if image_format == "PNG" else "RGB"
    Image.new(mode, size, color).save(stream, format=image_format)
    stream.seek(0)
    return stream


class RecordingAnalyzer:
    def __init__(self, result=None, error=None):
        self.result = result or {
            "title": "Silver laptop computer",
            "category": "electronics",
            "title_confidence": 0.84,
            "category_confidence": 0.92,
            "abstain_reason": "",
        }
        self.error = error
        self.calls = []

    def __call__(self, clean_jpeg):
        self.calls.append(clean_jpeg)
        if self.error:
            raise self.error
        return self.result


@pytest.fixture()
def vision_web(db_app):
    db_app.config.update(
        WTF_CSRF_ENABLED=False,
        SECRET_KEY="isolated-vision-test-secret",
        VISION_AI_ENABLED=True,
        VISION_AI_PROVIDER="openai",
        VISION_AI_MODEL="gpt-6-luna",
        VISION_AI_TIMEOUT_SECONDS=12,
    )
    return db_app.test_client()


def configure_analyzer(app, analyzer):
    app.config["VISION_AI_ANALYZER"] = analyzer
    return analyzer


def post_photo(client, filename="product.png", stream=None):
    return client.post(
        "/ai/vision-listing",
        data={"image": (stream or picture(), filename)},
        content_type="multipart/form-data",
    )


def business_counts(session):
    from app.models import Product, ListingSubmission, InteractionEvent
    return {
        model.__tablename__: session.scalar(select(func.count()).select_from(model))
        for model in (Product, ListingSubmission, InteractionEvent)
    }


def test_sell_page_has_disclosed_optional_vision_controls(
        vision_web, db_app, user_factory):
    configure_analyzer(db_app, RecordingAnalyzer())
    sign_in(vision_web, user_factory())
    page = Page(vision_web.get("/listings/new"))
    control = page.one("input", id="vision-ai-enabled", type="checkbox")
    assert "checked" in control["attrs"]
    disclosure = page.one("p", id="vision-ai-disclosure")
    assert "resized" in disclosure["text"].lower()
    assert "metadata-free" in disclosure["text"].lower()
    assert "OpenAI" in disclosure["text"]
    page.one("span", id="vision-ai-spinner", **{"aria-hidden": "true"})
    page.one("p", id="vision-ai-status", **{"aria-live": "polite"})
    page.one(id="title-ai-marker")
    page.one(id="category-ai-marker")
    described = page.one("input", id="image")["attrs"]["aria-describedby"].split()
    assert {"vision-ai-disclosure", "vision-ai-status"} <= set(described)


def test_vision_disabled_keeps_manual_form_and_no_active_control(
        vision_web, db_app, user_factory):
    db_app.config["VISION_AI_ENABLED"] = False
    db_app.config.pop("VISION_AI_ANALYZER", None)
    sign_in(vision_web, user_factory())
    page = Page(vision_web.get("/listings/new"))
    control = page.one("input", id="vision-ai-enabled", type="checkbox")
    assert "disabled" in control["attrs"] and "checked" not in control["attrs"]
    assert "unavailable" in page.text(id="vision-ai-disclosure").lower()
    page.one("input", id="image", type="file")
    page.one("input", id="title")
    page.one("select", id="category")
    page.one("button", type="submit")


def test_vision_endpoint_requires_login_and_enabled_provider(
        vision_web, db_app, user_factory):
    analyzer = configure_analyzer(db_app, RecordingAnalyzer())
    assert post_photo(vision_web).status_code == 302
    sign_in(vision_web, user_factory())
    db_app.config["VISION_AI_ENABLED"] = False
    response = post_photo(vision_web)
    assert response.status_code == 503
    assert "unavailable" in response.json["message"].lower()
    assert analyzer.calls == []


def test_csrf_protects_vision_endpoint(
        vision_web, db_app, user_factory):
    configure_analyzer(db_app, RecordingAnalyzer())
    sign_in(vision_web, user_factory())
    db_app.config["WTF_CSRF_ENABLED"] = True
    assert post_photo(vision_web).status_code == 400


def test_valid_photo_returns_suggestion_without_business_writes_or_files(
        vision_web, db_app, user_factory, db_session):
    analyzer = configure_analyzer(db_app, RecordingAnalyzer())
    sign_in(vision_web, user_factory())
    before = business_counts(db_session)
    upload_root = Path(db_app.config["UPLOAD_FOLDER"])
    response = post_photo(vision_web)
    assert response.status_code == 200
    assert response.headers["Cache-Control"].startswith("private")
    assert response.json == {
        "suggestion": {"title": "Silver laptop computer", "category": "electronics"},
        "confidence": {"title": 0.84, "category": 0.92},
        "message": "AI suggestions are ready. Review them before saving.",
    }
    assert business_counts(db_session) == before
    assert not upload_root.exists() or not list(upload_root.iterdir())
    assert len(analyzer.calls) == 1


def test_provider_receives_only_clean_bounded_jpeg(
        vision_web, db_app, user_factory):
    analyzer = configure_analyzer(db_app, RecordingAnalyzer())
    sign_in(vision_web, user_factory())
    source = picture(size=(2200, 1100), color=(100, 20, 160, 100))
    assert post_photo(vision_web, "private-name-with-location.png", source).status_code == 200
    assert len(analyzer.calls) == 1
    clean = analyzer.calls[0]
    assert b"private-name" not in clean
    with Image.open(BytesIO(clean)) as image:
        assert image.format == "JPEG"
        assert image.mode == "RGB"
        assert max(image.size) <= 1024
        assert not image.getexif()


@pytest.mark.parametrize(("payload", "filename", "message"), [
    (b"", "empty.png", "nonempty"),
    (b"not an image", "spoof.png", "readable"),
    (b"x" * (5 * 1024 * 1024 + 1), "large.jpg", "5 MiB"),
], ids=["empty", "spoofed", "over-five-mib"])
def test_bad_images_stop_before_provider(
        vision_web, db_app, user_factory, payload, filename, message):
    analyzer = configure_analyzer(db_app, RecordingAnalyzer())
    sign_in(vision_web, user_factory())
    response = post_photo(vision_web, filename, BytesIO(payload))
    assert response.status_code == 400
    assert message.lower() in response.json["message"].lower()
    assert analyzer.calls == []


def test_missing_and_ambiguous_file_payloads_stop_before_provider(
        vision_web, db_app, user_factory):
    analyzer = configure_analyzer(db_app, RecordingAnalyzer())
    sign_in(vision_web, user_factory())
    assert vision_web.post("/ai/vision-listing", data={}).status_code == 400
    response = vision_web.post(
        "/ai/vision-listing",
        data={"image": [(picture(), "one.png"), (picture(), "two.png")]},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert analyzer.calls == []


@pytest.mark.parametrize(("raw", "suggestion"), [
    ({"title": "Desk lamp", "category": "home_garden", "title_confidence": .65,
      "category_confidence": .65, "abstain_reason": ""},
     {"title": "Desk lamp", "category": "home_garden"}),
    ({"title": "Desk lamp", "category": "home_garden", "title_confidence": .64,
      "category_confidence": .91, "abstain_reason": ""},
     {"title": None, "category": "home_garden"}),
    ({"title": "Desk lamp", "category": "home_garden", "title_confidence": .91,
      "category_confidence": .64, "abstain_reason": ""},
     {"title": "Desk lamp", "category": None}),
    ({"title": "Desk lamp", "category": "home_garden", "title_confidence": .2,
      "category_confidence": .2, "abstain_reason": "unclear"}, None),
])
def test_result_validation_threshold_and_partial_acceptance(raw, suggestion):
    from app.ai.vision import validate_vision_result
    result = validate_vision_result(raw)
    assert result["suggestion"] == suggestion


@pytest.mark.parametrize("changes", [
    {"category": "ELECTRONICS"},
    {"category": "unknown"},
    {"title": "<script>alert(1)</script>"},
    {"title": "ab"},
    {"title": "x" * 81},
    {"title": "bad\x00title"},
    {"title_confidence": True},
    {"title_confidence": float("nan")},
    {"category_confidence": float("inf")},
    {"extra": "not allowed"},
])
def test_result_validation_rejects_untrusted_provider_output(changes):
    from app.ai.vision import InvalidVisionResult, validate_vision_result
    raw = {"title": "Wireless headphones", "category": "electronics",
           "title_confidence": .9, "category_confidence": .9,
           "abstain_reason": ""}
    raw.update(changes)
    with pytest.raises(InvalidVisionResult):
        validate_vision_result(raw)


def test_provider_failure_is_generic_and_secret_safe(
        vision_web, db_app, user_factory, caplog):
    secret = "sk-private-vision-canary"
    raw = "RAW_PROVIDER_BODY_CANARY"
    configure_analyzer(db_app, RecordingAnalyzer(error=TimeoutError(secret + raw)))
    sign_in(vision_web, user_factory())
    response = post_photo(vision_web, "private-file-canary.png")
    assert response.status_code in {502, 503}
    combined = response.get_data(as_text=True) + caplog.text
    assert "unavailable" in response.json["message"].lower()
    for private in (secret, raw, "private-file-canary"):
        assert private not in combined


def test_vision_rate_limit_is_separate_and_atomic(
        vision_web, db_app, user_factory):
    analyzer = configure_analyzer(db_app, RecordingAnalyzer())
    user = user_factory()
    sign_in(vision_web, user)
    for _ in range(10):
        assert post_photo(vision_web).status_code == 200
    limited = post_photo(vision_web)
    assert limited.status_code == 429 and "Retry-After" in limited.headers
    assert len(analyzer.calls) == 10
    # Existing text-AI bucket has a different scope.
    assert vision_web.post("/ai/category", data={}).status_code != 429


def test_openai_adapter_uses_narrow_stateless_structured_request(monkeypatch):
    from app.ai.openai_vision import OpenAIVisionProvider

    calls = []

    class Responses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return type("Response", (), {"output_text": json.dumps({
                "title": "City bicycle", "category": "sports_outdoors",
                "title_confidence": .91, "category_confidence": .88,
                "abstain_reason": "",
            })})()

    client = type("Client", (), {"responses": Responses()})()
    provider = OpenAIVisionProvider(client=client, model="gpt-6-luna", timeout=12)
    result = provider.analyze(b"\xff\xd8\xff\xd9")
    assert result["category"] == "sports_outdoors"
    assert len(calls) == 1
    request = calls[0]
    assert request["model"] == "gpt-6-luna"
    assert request["store"] is False
    assert request.get("tools", []) == []
    assert request["reasoning"]["effort"] == "none"
    serialized = json.dumps(request)
    assert "data:image/jpeg;base64," in serialized
    assert '"detail": "low"' in serialized
    assert "json_schema" in serialized
    assert all(category in serialized for category in ALLOWED_CATEGORIES)
    assert "username" not in serialized and "email" not in serialized


def test_configuration_defaults_disabled_and_validates_enabled_values(monkeypatch, tmp_path):
    from config import environment_settings

    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    for name in ("VISION_AI_ENABLED", "VISION_AI_PROVIDER", "VISION_AI_MODEL",
                 "VISION_AI_TIMEOUT_SECONDS", "GEMINI_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    settings = environment_settings(tmp_path)
    assert settings["VISION_AI_ENABLED"] is False
    assert settings["VISION_AI_PROVIDER"] == "gemini"
    assert settings["VISION_AI_MODEL"] == "gemini-3.5-flash-lite"
    assert "GEMINI_API_KEY" not in settings
    assert "OPENAI_API_KEY" not in settings
    monkeypatch.setenv("VISION_AI_ENABLED", "true")
    monkeypatch.setenv("VISION_AI_PROVIDER", "unsupported")
    with pytest.raises(ValueError, match="VISION_AI_PROVIDER"):
        environment_settings(tmp_path)
    monkeypatch.setenv("VISION_AI_PROVIDER", "gemini")
    monkeypatch.setenv("VISION_AI_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setenv("VISION_AI_TIMEOUT_SECONDS", "60")
    with pytest.raises(ValueError, match="VISION_AI_TIMEOUT_SECONDS"):
        environment_settings(tmp_path)


def test_client_source_has_race_dirty_and_privacy_guards():
    source = (PROJECT_ROOT / "app/static/js/market.js").read_text(encoding="utf-8")
    for token in (
        "/ai/vision-listing", "vision-ai-enabled", "vision-ai-status",
        "title-ai-marker", "category-ai-marker", "AbortController",
        "selectionSequence", "analysisSequence", "titleTouched",
        "categoryTouched", "applyingAi", "csrf_token", "textContent",
    ):
        assert token in source
    assert re.search(r"new\s+FormData\s*\(\s*\)", source)
    assert not re.search(r"new\s+FormData\s*\(\s*listingForm\s*\).*vision-listing",
                         source, re.S)
    assert "data.delete('image')" in source or 'data.delete("image")' in source
    assert ".submit(" not in source and "requestSubmit(" not in source


def test_default_category_is_untouched_until_the_seller_changes_it():
    source = (PROJECT_ROOT / "app/static/js/market.js").read_text(encoding="utf-8")
    # The select has a normal default value, but that is not a seller edit.
    assert re.search(r"let\s+categoryTouched\s*=\s*false\s*;", source)
    assert "category.addEventListener('change', markCategoryTouched)" in source


def test_vision_css_has_hidden_reduced_motion_and_mobile_safe_rules():
    css = (PROJECT_ROOT / "app/static/css/style.css").read_text(encoding="utf-8")
    for selector in (".vision-ai-option", ".vision-ai-spinner", ".ai-field-marker"):
        assert selector in css
    assert "prefers-reduced-motion: reduce" in css
    vision_rules = "\n".join(line for line in css.splitlines()
                             if "vision-ai" in line or "ai-field-marker" in line)
    assert "overflow-wrap" in css and "min-width" in css
    assert "[hidden]" in css


def test_edit_and_unrelated_forms_do_not_receive_vision_ui(
        vision_web, db_app, user_factory, product_factory):
    configure_analyzer(db_app, RecordingAnalyzer())
    owner = user_factory()
    product = product_factory(seller=owner)
    sign_in(vision_web, owner)
    for path in (f"/listings/{product.id}/edit", "/account/profile", "/products"):
        page = Page(vision_web.get(path))
        assert not page.find(id="vision-ai-enabled")
        assert not page.find(id="vision-ai-status")


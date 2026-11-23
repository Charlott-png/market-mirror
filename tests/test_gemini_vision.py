"""MM-024 contracts written before the live Gemini implementation."""

from io import BytesIO
import json
import os
from pathlib import Path

import pytest
from PIL import Image

from tests.test_marketplace import sign_in
from tests.test_seller_profile import Page


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_CATEGORIES = {
    "electronics", "home_garden", "clothing", "books_media",
    "sports_outdoors", "toys_games", "other",
}


def settings_environment(monkeypatch, **values):
    """Give environment_settings a deterministic, secret-safe environment."""
    names = (
        "APP_ENV", "DATABASE_URL", "TRUSTED_HOSTS", "UPLOAD_FOLDER",
        "AI_FOLDER", "VISION_AI_ENABLED", "VISION_AI_PROVIDER",
        "VISION_AI_MODEL", "VISION_AI_TIMEOUT_SECONDS", "GEMINI_API_KEY",
        "OPENAI_API_KEY",
    )
    for name in names:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SECRET_KEY", "s" * 32)
    for name, value in values.items():
        monkeypatch.setenv(name, str(value))


def clean_jpeg():
    stream = BytesIO()
    Image.new("RGB", (80, 60), "#7695a8").save(stream, format="JPEG")
    return stream.getvalue()


def test_local_dotenv_loads_without_overriding_process_environment(monkeypatch, tmp_path):
    from config import load_local_environment

    (tmp_path / ".env").write_text(
        "VISION_AI_PROVIDER=gemini\n"
        "VISION_AI_MODEL=from-private-file\n"
        "GEMINI_API_KEY=private-file-canary\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("VISION_AI_PROVIDER", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("VISION_AI_MODEL", "process-wins")
    load_local_environment(tmp_path)
    assert os.environ["VISION_AI_PROVIDER"] == "gemini"
    assert os.environ["VISION_AI_MODEL"] == "process-wins"
    assert os.environ["GEMINI_API_KEY"] == "private-file-canary"


def test_missing_dotenv_is_normal(monkeypatch, tmp_path):
    from config import load_local_environment

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert load_local_environment(tmp_path) is False
    assert "GEMINI_API_KEY" not in os.environ


def test_real_env_is_ignored_but_example_is_trackable():
    rules = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in rules
    assert "!.env.example" in rules


def test_gemini_is_disabled_default_and_secrets_never_enter_config(monkeypatch, tmp_path):
    from config import environment_settings

    settings_environment(
        monkeypatch,
        GEMINI_API_KEY="gemini-config-secret-canary",
        OPENAI_API_KEY="openai-config-secret-canary",
    )
    settings = environment_settings(tmp_path)
    assert settings["VISION_AI_ENABLED"] is False
    assert settings["VISION_AI_PROVIDER"] == "gemini"
    assert settings["VISION_AI_MODEL"] == "gemini-3.5-flash-lite"
    assert "GEMINI_API_KEY" not in settings
    assert "OPENAI_API_KEY" not in settings
    assert "secret-canary" not in repr(settings)


@pytest.mark.parametrize(("provider", "model"), [
    ("gemini", "gemini-3.5-flash-lite"),
    ("openai", "gpt-6-luna"),
])
def test_supported_provider_model_pairs(monkeypatch, tmp_path, provider, model):
    from config import environment_settings

    settings_environment(
        monkeypatch,
        VISION_AI_ENABLED="true",
        VISION_AI_PROVIDER=provider,
        VISION_AI_MODEL=model,
    )
    settings = environment_settings(tmp_path)
    assert settings["VISION_AI_PROVIDER"] == provider
    assert settings["VISION_AI_MODEL"] == model


@pytest.mark.parametrize(("provider", "model"), [
    ("gemini", "gpt-6-luna"),
    ("openai", "gemini-3.5-flash-lite"),
    ("unsupported", "gemini-3.5-flash-lite"),
])
def test_bad_provider_model_pairs_fail_safely(monkeypatch, tmp_path, provider, model):
    from config import environment_settings

    secret = "provider-model-secret-canary"
    settings_environment(
        monkeypatch,
        VISION_AI_ENABLED="true",
        VISION_AI_PROVIDER=provider,
        VISION_AI_MODEL=model,
        GEMINI_API_KEY=secret,
    )
    with pytest.raises(ValueError) as captured:
        environment_settings(tmp_path)
    assert "VISION_AI" in str(captured.value)
    assert secret not in str(captured.value)


def test_gemini_availability_requires_enablement_and_nonblank_key(db_app, monkeypatch):
    from app.ai.vision import vision_available

    db_app.config.update(
        VISION_AI_ENABLED=True,
        VISION_AI_PROVIDER="gemini",
        VISION_AI_MODEL="gemini-3.5-flash-lite",
    )
    db_app.config.pop("VISION_AI_ANALYZER", None)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with db_app.app_context():
        assert vision_available() is False
        monkeypatch.setenv("GEMINI_API_KEY", "   ")
        assert vision_available() is False
        monkeypatch.setenv("GEMINI_API_KEY", "test-only-gemini-key")
        assert vision_available() is True
        db_app.config["VISION_AI_ENABLED"] = False
        assert vision_available() is False


def test_openai_availability_remains_supported(db_app, monkeypatch):
    from app.ai.vision import vision_available

    db_app.config.update(
        VISION_AI_ENABLED=True,
        VISION_AI_PROVIDER="openai",
        VISION_AI_MODEL="gpt-6-luna",
    )
    db_app.config.pop("VISION_AI_ANALYZER", None)
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-openai-key")
    with db_app.app_context():
        assert vision_available() is True


def test_sell_page_enables_real_gemini_and_discloses_free_tier_data_use(
        db_app, user_factory, monkeypatch):
    db_app.config.update(
        WTF_CSRF_ENABLED=False,
        VISION_AI_ENABLED=True,
        VISION_AI_PROVIDER="gemini",
        VISION_AI_MODEL="gemini-3.5-flash-lite",
    )
    db_app.config.pop("VISION_AI_ANALYZER", None)
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-gemini-key")
    client = db_app.test_client()
    sign_in(client, user_factory())
    page = Page(client.get("/listings/new"))
    control = page.one("input", id="vision-ai-enabled", type="checkbox")
    assert "disabled" not in control["attrs"]
    assert "checked" in control["attrs"]
    disclosure = page.text(id="vision-ai-disclosure").lower()
    assert "google gemini" in disclosure
    assert "metadata-free" in disclosure
    assert "free" in disclosure
    assert "improve" in disclosure


def test_sell_page_missing_gemini_key_keeps_complete_manual_fallback(
        db_app, user_factory, monkeypatch):
    db_app.config.update(
        WTF_CSRF_ENABLED=False,
        VISION_AI_ENABLED=True,
        VISION_AI_PROVIDER="gemini",
        VISION_AI_MODEL="gemini-3.5-flash-lite",
    )
    db_app.config.pop("VISION_AI_ANALYZER", None)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    client = db_app.test_client()
    sign_in(client, user_factory())
    page = Page(client.get("/listings/new"))
    assert "disabled" in page.one("input", id="vision-ai-enabled")["attrs"]
    assert "unavailable" in page.text(id="vision-ai-disclosure").lower()
    page.one("input", id="image", type="file")
    page.one("input", id="title")
    page.one("select", id="category")
    page.one("button", type="submit")


def test_gemini_adapter_sends_one_clean_structured_narrow_request():
    from app.ai.gemini_vision import GeminiVisionProvider

    calls = []

    class Models:
        def generate_content(self, **kwargs):
            calls.append(kwargs)
            return type("Response", (), {"text": json.dumps({
                "title": "City bicycle",
                "category": "sports_outdoors",
                "title_confidence": 0.91,
                "category_confidence": 0.88,
                "abstain_reason": "",
            })})()

    client = type("Client", (), {"models": Models()})()
    jpeg = clean_jpeg()
    provider = GeminiVisionProvider(
        client=client,
        model="gemini-3.5-flash-lite",
        timeout=12,
    )
    result = provider.analyze(jpeg)
    assert result["category"] == "sports_outdoors"
    assert len(calls) == 1
    request = calls[0]
    assert request["model"] == "gemini-3.5-flash-lite"
    assert len(request["contents"]) == 2
    assert any(getattr(getattr(part, "inline_data", None), "data", None) == jpeg
               for part in request["contents"])
    configuration = request["config"]
    assert configuration.response_mime_type == "application/json"
    category_schema = configuration.response_json_schema["properties"]["category"]
    assert set(category_schema["enum"]) == ALLOWED_CATEGORIES
    serialized = repr(request)
    assert "username" not in serialized.lower()
    assert "email" not in serialized.lower()
    assert "filename" not in serialized.lower()
    assert "google_search" not in serialized.lower()
    assert configuration.tools == []


def test_gemini_client_uses_bounded_timeout_and_no_retry(monkeypatch):
    import app.ai.gemini_vision as adapter

    created = []

    class FakeClient:
        def __init__(self, **kwargs):
            created.append(kwargs)

    monkeypatch.setenv("GEMINI_API_KEY", "gemini-client-secret-canary")
    monkeypatch.setattr(adapter.genai, "Client", FakeClient)
    provider = adapter.GeminiVisionProvider(model="gemini-3.5-flash-lite", timeout=12)
    assert provider.client is not None and len(created) == 1
    assert created[0]["api_key"] == "gemini-client-secret-canary"
    options = created[0]["http_options"]
    assert options.timeout == 12000
    assert options.retry_options.attempts == 1


@pytest.mark.parametrize("response_text", ["", "not-json", "[]", "{}"])
def test_gemini_adapter_rejects_empty_or_malformed_response(response_text):
    from app.ai.gemini_vision import GeminiVisionProvider, GeminiVisionError

    class Models:
        def generate_content(self, **kwargs):
            return type("Response", (), {"text": response_text})()

    provider = GeminiVisionProvider(
        client=type("Client", (), {"models": Models()})(),
        model="gemini-3.5-flash-lite",
        timeout=12,
    )
    with pytest.raises(GeminiVisionError):
        provider.analyze(clean_jpeg())


def test_gemini_provider_failure_never_leaks_secret_or_raw_body(
        db_app, user_factory, monkeypatch, caplog):
    from tests.test_ai_vision import post_photo

    secret = "gemini-private-secret-canary"
    raw = "GEMINI_RAW_BODY_CANARY"
    db_app.config.update(
        WTF_CSRF_ENABLED=False,
        VISION_AI_ENABLED=True,
        VISION_AI_PROVIDER="gemini",
        VISION_AI_MODEL="gemini-3.5-flash-lite",
    )
    db_app.config.pop("VISION_AI_ANALYZER", None)
    monkeypatch.setenv("GEMINI_API_KEY", secret)

    class FailingProvider:
        def analyze(self, clean_bytes):
            raise RuntimeError(secret + raw)

    monkeypatch.setattr("app.ai.vision.build_vision_provider", lambda: FailingProvider())
    client = db_app.test_client()
    sign_in(client, user_factory())
    response = post_photo(client, filename="private-gemini-file.png")
    assert response.status_code in {502, 503}
    combined = response.get_data(as_text=True) + caplog.text
    assert "unavailable" in response.json["message"].lower()
    for private in (secret, raw, "private-gemini-file"):
        assert private not in combined


def test_examples_and_client_source_never_contain_real_key_patterns():
    example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
    javascript = (PROJECT_ROOT / "app/static/js/market.js").read_text(encoding="utf-8")
    assert "GEMINI_API_KEY=" in example
    assert "REPLACE" in example
    assert "GEMINI_API_KEY" not in javascript
    assert "OPENAI_API_KEY" not in javascript


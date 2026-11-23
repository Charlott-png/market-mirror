"""Environment settings. Test overrides are applied by the application factory."""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv


class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Prevent SQL errors from printing bound values such as hashes or email addresses.
    SQLALCHEMY_ENGINE_OPTIONS = {"hide_parameters": True}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    MAX_CONTENT_LENGTH = 26 * 1024 * 1024
    # Image analysis is deliberately off unless the operator enables it.
    VISION_AI_ENABLED = False
    VISION_AI_PROVIDER = "gemini"
    VISION_AI_MODEL = "gemini-3.5-flash-lite"
    VISION_AI_TIMEOUT_SECONDS = 12
    # Product discovery is separate from image analysis and opt-in by default.
    SHOP_ASSISTANT_ENABLED = False
    SHOP_ASSISTANT_MODEL = "gemini-3.5-flash-lite"
    SHOP_ASSISTANT_TIMEOUT_SECONDS = 12
    CHECKOUT_TOKEN_MAX_AGE = 1800


def _environment_flag(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false.")


def load_local_environment(project_root):
    """Load a private local .env without replacing real process settings."""
    path = Path(project_root) / ".env"
    if not path.is_file():
        return False
    return bool(load_dotenv(path, override=False))


def environment_settings(instance_path):
    """Read environment values each time an app is created, not at import time."""
    default_path = Path(instance_path) / "market-mirror.sqlite"
    environment = os.environ.get("APP_ENV", "development").lower()
    database_url = os.environ.get("DATABASE_URL")
    secret = os.environ.get("SECRET_KEY")
    if not secret or len(secret) < 32:
        raise ValueError("Set SECRET_KEY to a random value of at least 32 characters.")
    if environment == "production" and not database_url:
        raise ValueError("Production requires DATABASE_URL.")
    hosts = [host.strip() for host in os.environ.get("TRUSTED_HOSTS", "").split(",") if host.strip()]
    if environment == "production":
        if not database_url.startswith("postgresql+psycopg://"):
            raise ValueError("Production requires a postgresql+psycopg DATABASE_URL.")
        if not hosts or not os.environ.get("UPLOAD_FOLDER"):
            raise ValueError("Production requires TRUSTED_HOSTS and a persistent UPLOAD_FOLDER.")
    vision_enabled = _environment_flag("VISION_AI_ENABLED")
    vision_provider = os.environ.get("VISION_AI_PROVIDER", "gemini").strip().lower()
    if vision_enabled and vision_provider not in {"gemini", "openai"}:
        raise ValueError("VISION_AI_PROVIDER must be gemini or openai when vision analysis is enabled.")
    default_model = "gpt-6-luna" if vision_provider == "openai" else "gemini-3.5-flash-lite"
    vision_model = os.environ.get("VISION_AI_MODEL", default_model).strip()
    if (not vision_model or len(vision_model) > 80 or
            any(ord(character) < 32 for character in vision_model)):
        raise ValueError("VISION_AI_MODEL must be a short printable model name.")
    if vision_enabled:
        if vision_provider == "gemini" and not vision_model.startswith("gemini-"):
            raise ValueError("VISION_AI_MODEL must be a Gemini model for the gemini provider.")
        if vision_provider == "openai" and vision_model.startswith("gemini-"):
            raise ValueError("VISION_AI_MODEL must be an OpenAI model for the openai provider.")
    try:
        vision_timeout = int(os.environ.get("VISION_AI_TIMEOUT_SECONDS", "12"))
    except ValueError:
        raise ValueError("VISION_AI_TIMEOUT_SECONDS must be a whole number from 3 to 30.") from None
    if not 3 <= vision_timeout <= 30:
        raise ValueError("VISION_AI_TIMEOUT_SECONDS must be from 3 to 30.")
    shop_enabled = _environment_flag("SHOP_ASSISTANT_ENABLED")
    shop_model = os.environ.get("SHOP_ASSISTANT_MODEL", "gemini-3.5-flash-lite").strip()
    if (not shop_model or len(shop_model) > 80 or
            any(ord(character) < 32 for character in shop_model)):
        raise ValueError("SHOP_ASSISTANT_MODEL must be a short printable model name.")
    if shop_enabled and not shop_model.startswith("gemini-"):
        raise ValueError("SHOP_ASSISTANT_MODEL must be a Gemini model when the assistant is enabled.")
    try:
        shop_timeout = int(os.environ.get("SHOP_ASSISTANT_TIMEOUT_SECONDS", "12"))
    except ValueError:
        raise ValueError("SHOP_ASSISTANT_TIMEOUT_SECONDS must be a whole number from 3 to 30.") from None
    if not 3 <= shop_timeout <= 30:
        raise ValueError("SHOP_ASSISTANT_TIMEOUT_SECONDS must be from 3 to 30.")
    return {
        "APP_ENV": environment,
        "DEBUG": False,
        "TRUSTED_HOSTS": hosts or None,
        "SECRET_KEY": secret,
        "SESSION_COOKIE_SECURE": environment == "production",
        "UPLOAD_FOLDER": os.environ.get("UPLOAD_FOLDER", str(Path(instance_path) / "uploads")),
        "AI_FOLDER": os.environ.get("AI_FOLDER", str(Path(instance_path) / "ai")),
        "SQLALCHEMY_DATABASE_URI": database_url or f"sqlite:///{default_path.as_posix()}",
        "VISION_AI_ENABLED": vision_enabled,
        "VISION_AI_PROVIDER": vision_provider,
        "VISION_AI_MODEL": vision_model,
        "VISION_AI_TIMEOUT_SECONDS": vision_timeout,
        "SHOP_ASSISTANT_ENABLED": shop_enabled,
        "SHOP_ASSISTANT_MODEL": shop_model,
        "SHOP_ASSISTANT_TIMEOUT_SECONDS": shop_timeout,
    }

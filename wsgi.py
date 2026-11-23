"""Production-style entry point; migrations are a separate explicit step."""

from app import create_app

application = create_app()

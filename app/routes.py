"""Public routes for the Market Mirror foundation."""

from flask import Blueprint, jsonify, render_template


main_blueprint = Blueprint("main", __name__)


@main_blueprint.get("/")
def home():
    """Display the public Market Mirror welcome page."""
    return render_template("index.html")


@main_blueprint.get("/health")
def health():
    """Return a small, non-sensitive response for health checks."""
    return jsonify(service="market-mirror", status="ok")

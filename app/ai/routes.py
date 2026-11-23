"""Small, read-only prediction endpoints and explicit offline commands."""

import csv
from pathlib import Path

import click
from flask import Blueprint, abort, current_app, jsonify, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Product
from app.models.product import CATEGORIES, CONDITIONS
from app.ai.inference import category_suggestion, price_suggestion
from app.ai.recommendations import recommend, build_index
from app.security import consume_limit
from app.images import normalized_image_bytes
from app.ai.vision import analyze_listing_image, vision_available
from app.ai.shop_assistant import (InvalidShopRequest, answer_shop_query,
                                   shop_assistant_available,
                                   validate_shop_request)

ai = Blueprint("ai", __name__)


def private_json(payload, status=200):
    response = jsonify(payload)
    response.status_code = status
    response.headers["Cache-Control"] = "private, no-store"
    return response


@ai.post("/ai/shop-assistant")
@login_required
def shop_assistant():
    """Return trusted links around a validated, read-only Gemini suggestion."""
    if not shop_assistant_available():
        return private_json({
            "message": "AI Shop Assistant is unavailable. Use Explore to search products."
        }, 503)
    if (not request.is_json or
            (request.content_length is not None and request.content_length > 8192)):
        return private_json({"message": "Send one short shop-assistant question."}, 400)
    try:
        query, history = validate_shop_request(request.get_json(silent=True))
    except InvalidShopRequest:
        return private_json({"message": "Enter a valid question of up to 300 characters."}, 400)

    consume_limit("shop-assistant", str(current_user.id), 15, 600)
    try:
        return private_json(answer_shop_query(query, history))
    except Exception:
        # Provider exceptions can contain prompt/catalogue/secret material.
        current_app.logger.warning("shop_assistant_provider_unavailable")
        return private_json({
            "message": "AI Shop Assistant is unavailable. Use Explore to search products."
        }, 503)


@ai.post("/ai/vision-listing")
@login_required
def vision_listing():
    """Analyze one temporary, cleaned image without creating a listing."""
    if not vision_available():
        return jsonify(message="AI image suggestions are unavailable. Enter the details yourself."), 503

    uploads = request.files.getlist("image")
    if len(uploads) != 1 or not uploads[0].filename:
        return jsonify(message="Choose exactly one product photo."), 400

    consume_limit("vision-ai", str(current_user.id), 10, 600)
    try:
        clean_jpeg = normalized_image_bytes(uploads[0], max_dimension=1024, quality=80)
    except ValueError as error:
        return jsonify(message=str(error)), 400

    try:
        result = analyze_listing_image(clean_jpeg)
    except Exception:
        # Provider exceptions can contain request bytes, filenames or secrets,
        # so record only a stable event name and return a generic explanation.
        current_app.logger.warning("vision_ai_provider_unavailable")
        return jsonify(message="AI image suggestions are unavailable. Enter the details yourself."), 503

    suggestion = result["suggestion"]
    if suggestion is None:
        message = "The image was unclear. Enter the title and category yourself."
    else:
        message = "AI suggestions are ready. Review them before saving."
    response = jsonify(suggestion=suggestion, confidence=result["confidence"], message=message)
    response.headers["Cache-Control"] = "private, no-store"
    return response


def inputs(require_choices=False):
    values = {key: request.form.get(key, "").strip() for key in ("title", "description", "category", "condition")}
    if len(values["title"]) > 120 or len(values["description"]) > 5000:
        abort(400, "Title or description is too long.")
    if require_choices and (not 3 <= len(values["title"]) <= 120 or not 10 <= len(values["description"]) <= 5000
                            or values["category"] not in CATEGORIES or values["condition"] not in CONDITIONS):
        abort(400, "Provide a valid title, description, category and condition.")
    return values


@ai.post("/ai/category")
@login_required
def category():
    consume_limit("ai", str(current_user.id), 30, 600)
    return jsonify(category_suggestion(current_app.config["AI_FOLDER"], inputs()))


@ai.post("/ai/price")
@login_required
def price():
    consume_limit("ai", str(current_user.id), 30, 600)
    return jsonify(price_suggestion(current_app.config["AI_FOLDER"], inputs(True)))


@ai.get("/recommendations")
def recommendations():
    raw = request.args.get("product_id")
    identifier = None
    if raw is not None:
        if not raw.isascii() or not raw.isdigit() or len(raw) > 10:
            abort(400, "Invalid product identifier.")
        identifier = int(raw)
        product = db.session.get(Product, identifier)
        if product is None or product.status not in {"active", "sold"}:
            abort(404)
    return jsonify(recommend(current_user.id if current_user.is_authenticated else None, identifier))


def register_ai_commands(application):
    @application.cli.group("ai")
    def commands():
        """Train trusted local models and refresh public catalogue features."""

    @commands.command("train")
    @click.option("--csv-file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
    def train(csv_file):
        """Train on project-authored synthetic data, or an operator-approved CSV."""
        from app.ai.data import synthetic_rows
        from app.ai.training import train_models
        rows = synthetic_rows()
        if csv_file:
            with csv_file.open(encoding="utf-8-sig", newline="") as source:
                rows = list(csv.DictReader(source))
            for row in rows:
                if row.get("synthetic") in {"true", "false"}:
                    row["synthetic"] = row["synthetic"] == "true"
        try:
            report = train_models(rows, current_app.config["AI_FOLDER"])
        except ValueError as error:
            raise click.ClickException(str(error)) from error
        click.echo(f"Trained {'synthetic' if report['synthetic'] else 'source-provided'} dataset. "
                   f"Category macro-F1: {report['category']['macro_f1']:.4f}; "
                   f"price MAE: ${report['price']['mae']:.2f}. Read evaluation.json for limitations.")

    @commands.command("index")
    def index():
        click.echo(f"Indexed {build_index(current_app.config['AI_FOLDER'])} active products.")

"""Offline public-catalogue index with live visibility and consent checks."""

from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import json

import joblib
import numpy as np
import sklearn
from flask import current_app
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.extensions import db
from app.models import Product, User, InteractionEvent
from app.ai.training import save_json


def build_index(directory):
    """An explicit CLI operation, never called by a web request."""
    products = db.session.execute(db.select(Product).where(Product.status == "active").order_by(Product.id)).scalars().all()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if not products:
        # An empty index is valid and cannot expose a previous catalogue.
        bundle = {"ids": [], "versions": [], "vectorizer": None, "matrix": None}
    else:
        vectorizer = TfidfVectorizer(max_features=10000, ngram_range=(1, 2))
        matrix = vectorizer.fit_transform([f"{p.title} {p.description} {p.category}" for p in products])
        bundle = {"ids": [p.id for p in products], "versions": [p.version for p in products],
                  "vectorizer": vectorizer, "matrix": matrix}
    temporary = directory / "catalogue.pending"
    artifact = directory / "catalogue.joblib"
    joblib.dump(bundle, temporary)
    temporary.replace(artifact)
    save_json(directory / "catalogue-manifest.json", {"schema": 1, "sklearn_version": sklearn.__version__,
        "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(), "count": len(products)})
    return len(products)


def load_index():
    directory = Path(current_app.config["AI_FOLDER"])
    manifest = json.loads((directory / "catalogue-manifest.json").read_text(encoding="utf-8"))
    artifact = directory / "catalogue.joblib"
    if manifest["schema"] != 1 or manifest["sklearn_version"] != sklearn.__version__:
        raise ValueError("Incompatible catalogue index")
    if artifact.stat().st_size > 64 * 1024 * 1024 or hashlib.sha256(artifact.read_bytes()).hexdigest() != manifest["sha256"]:
        raise ValueError("Invalid catalogue index")
    return joblib.load(artifact)


def recommend(viewer_id=None, product_id=None):
    # Bound request work. This classroom implementation considers the latest
    # 500 active listings; a large marketplace needs a dedicated retrieval layer.
    query = db.select(Product).where(Product.status == "active")
    if viewer_id:
        query = query.where(Product.seller_id != viewer_id)
    if product_id:
        query = query.where(Product.id != product_id)
    candidates = db.session.execute(query.order_by(Product.created_at.desc(), Product.id.desc()).limit(500)).scalars().all()
    base = db.session.get(Product, product_id) if product_id else None
    scores, reasons = {}, {}
    try:
        index = load_index()
        positions = {identifier: i for i, identifier in enumerate(index["ids"])}
        vectorizer, matrix = index["vectorizer"], index["matrix"]
        profile = None
        if base and base.status in {"active", "sold"} and vectorizer is not None:
            profile = vectorizer.transform([f"{base.title} {base.description} {base.category}"])
        elif viewer_id and vectorizer is not None:
            user = db.session.get(User, viewer_id)
            if user and user.personalization:
                events = db.session.execute(db.select(InteractionEvent, Product).join(Product, Product.id == InteractionEvent.product_id)
                    .where(InteractionEvent.user_id == viewer_id, Product.status == "active",
                           InteractionEvent.created_at >= datetime.now(timezone.utc) - timedelta(days=90))
                    .order_by(InteractionEvent.created_at.desc(), InteractionEvent.id.desc()).limit(500)).all()
                if events:
                    vectors = vectorizer.transform([f"{p.title} {p.description} {p.category}" for _, p in events])
                    weights = np.array([{"view": 1, "save": 3, "contact": 4}[event.kind] for event, _ in events])
                    profile = np.asarray(vectors.multiply(weights[:, None]).sum(axis=0)) / weights.sum()
        if profile is not None:
            similarity = cosine_similarity(profile, matrix)[0]
            for product in candidates:
                position = positions.get(product.id)
                # Edited rows have stale features, so use the recent-item fallback.
                if position is not None and index["versions"][position] == product.version:
                    score = float(similarity[position])
                    if score > 0:
                        scores[product.id] = score
                        reasons[product.id] = ("Similar public description and category" if base else
                                               "Similar to your opted-in activity")
    except Exception:
        pass  # Missing/corrupt artifacts must not take down the marketplace.

    # Similarity ties use the product ID, as specified. Recency is only the
    # fallback ordering for products without a useful indexed similarity score.
    ranked = sorted(candidates, key=lambda p: (0, -scores[p.id], p.id)
                    if p.id in scores else (1, -p.created_at.timestamp(), p.id))
    selected, sellers, categories = [], Counter(), Counter()
    # For the fallback, prefer a new category, then recency. Always honor the
    # two-per-seller cap first; relax only when there are too few alternatives.
    while ranked and len(selected) < 6:
        eligible = [p for p in ranked if sellers[p.seller_id] < 2]
        if not eligible:
            eligible = ranked
        if not scores:
            product = min(eligible, key=lambda p: (categories[p.category], -p.created_at.timestamp(), p.id))
        else:
            product = eligible[0]
        selected.append(product)
        ranked.remove(product)
        sellers[product.seller_id] += 1
        categories[product.category] += 1
    return {"items": [{"id": p.id, "title": p.title, "price": str(p.price), "currency": "USD",
                       "reason": reasons.get(p.id, "Recent active listing; selected for variety")}
                      for p in selected],
            "message": "Suggestions are not endorsements." if selected else "No available products to recommend yet."}

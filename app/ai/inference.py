"""Load trusted local artifacts, validate compatibility, and abstain on failure."""

from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import hashlib
import json
import math

import joblib
import sklearn

from app.models.product import CATEGORIES


def load_bundle(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest["schema"] != 1 or manifest["sklearn_version"] != sklearn.__version__ or manifest["categories"] != sorted(CATEGORIES):
        raise ValueError("Incompatible model manifest.")
    artifact = directory / "models.joblib"
    if artifact.stat().st_size > 64 * 1024 * 1024 or hashlib.sha256(artifact.read_bytes()).hexdigest() != manifest["artifact_sha256"]:
        raise ValueError("Model checksum mismatch.")
    # A checksum detects corruption, not malicious authors. This directory must
    # contain only artifacts created by our offline CLI; no upload route accepts models.
    return joblib.load(artifact), manifest


def abstain(message):
    return {"value": None, "message": message, "model_version": None}


def category_suggestion(directory, values):
    try:
        bundle, manifest = load_bundle(directory)
        model = bundle["category"]
        features = model.named_steps["features"].transform([values])
        if not bundle["category_enabled"] or features.nnz == 0:
            return abstain("No confident suggestion; choose a category.")
        probabilities = model.predict_proba([values])[0]
        index = int(probabilities.argmax())
        score = float(probabilities[index])
        if score < .60:
            return abstain("No confident suggestion; choose a category.")
        category = str(model.classes_[index])
        prefix = "Synthetic classroom model: " if bundle["synthetic"] else "Suggested category: "
        return {"value": category, "score": score, "model_version": manifest["model_version"],
                "message": prefix + CATEGORIES[category] + ". Review before applying; the score is not certainty."}
    except Exception:
        # Optional AI must not prevent a seller from entering valid manual data.
        return abstain("Category suggestions are unavailable. Choose a category manually.")


def price_suggestion(directory, values):
    try:
        bundle, manifest = load_bundle(directory)
        if bundle["category_counts"].get(values["category"], 0) < 10:
            return abstain("Not enough data. Enter your own price.")
        if bundle["price_method"] == "ridge":
            estimate = float(bundle["price"].predict([values])[0])
        else:
            table = bundle["medians"]
            estimate = table.get(values["category"] + ":" + values["condition"], table.get(values["category"], table["global"]))
        if not math.isfinite(estimate) or not .01 <= estimate <= 9999999.99:
            return abstain("The model could not produce a suitable price. Enter your own price.")
        value = Decimal(str(estimate)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        prefix = "Synthetic classroom estimate: " if bundle["synthetic"] else "Suggested asking price: "
        return {"value": str(value), "currency": "USD", "method": bundle["price_method"],
                "model_version": manifest["model_version"],
                "message": f"{prefix}${value} USD. This is advice, not a guaranteed sale price."}
    except Exception:
        return abstain("Price suggestions are unavailable. Enter your own price.")

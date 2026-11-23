"""Offline pipelines: fitting happens here, never in a request handler."""

from collections import Counter, defaultdict
from pathlib import Path
import hashlib
import json

import joblib
import numpy as np
import sklearn
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (accuracy_score, f1_score, classification_report,
                             confusion_matrix, mean_absolute_error, median_absolute_error)
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.preprocessing import FunctionTransformer

from app.ai.data import prepare_dataset
from app.models.product import CATEGORIES


def listing_texts(rows):
    return [row["title"] + " " + row["description"] for row in rows]


def structured_features(rows):
    # This allow-list deliberately excludes target price, IDs, and provenance.
    return [{"category": row["category"], "condition": row["condition"]} for row in rows]


def text_features():
    return Pipeline([("text", FunctionTransformer(listing_texts, validate=False)),
                     ("tfidf", TfidfVectorizer(max_features=10000, ngram_range=(1, 2)))])


def baseline_table(train):
    grouped = defaultdict(list)
    for row in train:
        for key in (row["category"] + ":" + row["condition"], row["category"], "global"):
            grouped[key].append(float(row["price"]))
    return {key: float(np.median(prices)) for key, prices in grouped.items()}


def baseline_prices(rows, table):
    return np.array([table.get(row["category"] + ":" + row["condition"],
                    table.get(row["category"], table["global"])) for row in rows])


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")


def train_models(rows, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    prepared = prepare_dataset(rows)
    train, validation, test = (prepared[key] for key in ("train", "validation", "test"))
    y_train = [row["category"] for row in train]
    y_test = [row["category"] for row in test]
    category = Pipeline([("features", text_features()),
                         ("classifier", LogisticRegression(C=4, max_iter=1000, random_state=42))])
    category.fit(train, y_train)
    predicted = category.predict(test)
    probabilities = category.predict_proba(test).max(axis=1)
    suggested = probabilities >= .60
    majority = Counter(y_train).most_common(1)[0][0]
    baseline_f1 = f1_score(y_test, [majority] * len(test), average="macro", zero_division=0)
    category_f1 = f1_score(y_test, predicted, average="macro", zero_division=0)

    price = Pipeline([("features", FeatureUnion([
        ("text", text_features()),
        ("choices", Pipeline([("select", FunctionTransformer(structured_features, validate=False)),
                               ("encode", DictVectorizer())])),
    ])), ("regressor", Ridge(alpha=10, solver="lsqr"))])
    price.fit(train, np.array([float(row["price"]) for row in train]))
    medians = baseline_table(train)
    validation_targets = np.array([float(row["price"]) for row in validation])
    validation_predictions = price.predict(validation)
    validation_baseline = baseline_prices(validation, medians)
    # Select using validation only. Test rows remain the final comparison.
    method = "ridge" if mean_absolute_error(validation_targets, validation_predictions) < mean_absolute_error(validation_targets, validation_baseline) else "category-median"
    validation_selected = validation_predictions if method == "ridge" else validation_baseline
    error_range = float(np.percentile(np.abs(validation_targets - validation_selected), 80))
    targets = np.array([float(row["price"]) for row in test])
    test_baseline = baseline_prices(test, medians)
    estimates = price.predict(test) if method == "ridge" else test_baseline
    per_category = {}
    for key in CATEGORIES:
        mask = np.array([row["category"] == key for row in test])
        per_category[key] = {"count": int(mask.sum()), "mae": float(mean_absolute_error(targets[mask], estimates[mask]))}
    errors = np.abs(targets - estimates)
    worst = np.argsort(-errors)[:5]
    report = {
        "synthetic": prepared["synthetic"], "dataset_sha256": prepared["dataset_sha256"],
        "random_seed": 42, "sklearn_version": sklearn.__version__,
        "split_counts": {key: len(prepared[key]) for key in ("train", "validation", "test")},
        "class_counts": prepared["class_counts"], "rejected_count": prepared["rejected_count"],
        "limitations": "Synthetic classroom patterns and invented asking prices; these results do not measure real-world market performance.",
        "category": {"test_count": len(test), "macro_f1": float(category_f1),
            "baseline_macro_f1": float(baseline_f1), "accuracy": float(accuracy_score(y_test, predicted)),
            "coverage": float(suggested.mean()), "suggestion_accuracy": float(accuracy_score(np.array(y_test)[suggested], predicted[suggested])) if suggested.any() else None,
            "per_class": classification_report(y_test, predicted, output_dict=True, zero_division=0),
            "labels": sorted(CATEGORIES), "confusion_matrix": confusion_matrix(y_test, predicted, labels=sorted(CATEGORIES)).tolist()},
        "price": {"test_count": len(test), "method": method,
            "mae": float(mean_absolute_error(targets, estimates)), "median_absolute_error": float(median_absolute_error(targets, estimates)),
            "baseline_mae": float(mean_absolute_error(targets, test_baseline)),
            "validation_model_mae": float(mean_absolute_error(validation_targets, validation_predictions)),
            "validation_baseline_mae": float(mean_absolute_error(validation_targets, validation_baseline)),
            "empirical_error_range": error_range, "per_category": per_category,
            "largest_errors": [{"product_id": test[i]["product_id"], "actual": float(targets[i]),
                                "estimate": float(estimates[i]), "absolute_error": float(errors[i])} for i in worst]},
    }
    bundle = {"category": category, "price": price, "medians": medians,
              "price_method": method, "category_enabled": category_f1 > baseline_f1,
              "category_counts": dict(Counter(y_train)), "error_range": error_range,
              "synthetic": prepared["synthetic"]}
    artifact = directory / "models.joblib"
    temporary = directory / "models.pending"
    joblib.dump(bundle, temporary)
    temporary.replace(artifact)
    manifest = {"schema": 1, "sklearn_version": sklearn.__version__, "dataset_sha256": prepared["dataset_sha256"],
                "model_version": "mm-" + prepared["dataset_sha256"][:12], "categories": sorted(CATEGORIES),
                "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(), "synthetic": prepared["synthetic"]}
    save_json(directory / "manifest.json", manifest)
    save_json(directory / "evaluation.json", report)
    save_json(directory / "splits.json", {key: [{"id": row["product_id"], "group": row["duplicate_group"]} for row in prepared[key]] for key in ("train", "validation", "test")})
    save_json(directory / "quarantine.json", prepared["rejected"])
    save_json(directory / "data-card.json", {"sources": sorted({row["source"] for row in train + validation + test}),
        "licences": sorted({row["licence"] for row in train + validation + test}), "synthetic": prepared["synthetic"],
        "dataset_sha256": prepared["dataset_sha256"], "fields": list(train[0]),
        "cleaning": "Validate fields and prices; quarantine invalid rows and conflicting duplicates; group split before fitting.",
        "limitations": report["limitations"], "price_type": "fictional asking price" if prepared["synthetic"] else "source-defined asking price"})
    return report

"""MM-011–014 acceptance tests, defined before the ML implementation."""

import json
from decimal import Decimal

import pytest


def test_dataset_validation_quarantine_and_group_splits():
    from app.ai.data import synthetic_rows, prepare_dataset
    rows = synthetic_rows()
    rows.append({**rows[0], "product_id": "bad-price", "price": "NaN"})
    rows.append({**rows[1], "product_id": "bad-source", "source": ""})
    report = prepare_dataset(rows)
    assert report["rejected_count"] == 2
    assert report["synthetic"] is True
    groups = [set(row["duplicate_group"] for row in report[split]) for split in ("train", "validation", "test")]
    assert not groups[0] & groups[1] and not groups[1] & groups[2] and not groups[0] & groups[2]
    for split in ("train", "validation", "test"):
        assert len({row["category"] for row in report[split]}) == 7
    again = prepare_dataset(rows)
    assert report == again


def test_dataset_insufficient_data_stops_and_group_conflicts_rejected():
    from app.ai.data import synthetic_rows, prepare_dataset
    rows = synthetic_rows()
    with pytest.raises(ValueError, match="groups"):
        prepare_dataset(rows[:4])
    copied = {**rows[0], "product_id": "duplicate-copy", "duplicate_group": "different-group"}
    report = prepare_dataset(rows + [copied])
    assert report["rejected_count"] == 1


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    from app.ai.data import synthetic_rows
    from app.ai.training import train_models
    directory = tmp_path_factory.mktemp("trusted-ai")
    report = train_models(synthetic_rows(), directory)
    return directory, report


def test_training_report_has_real_baselines_and_provenance(trained):
    folder, report = trained
    assert report["synthetic"] is True
    assert report["category"]["test_count"] == report["price"]["test_count"]
    assert 0 <= report["category"]["macro_f1"] <= 1
    assert "baseline_macro_f1" in report["category"]
    assert report["price"]["mae"] >= 0 and report["price"]["baseline_mae"] >= 0
    assert "per_class" in report["category"] and "per_category" in report["price"]
    assert len(report["dataset_sha256"]) == 64
    assert (folder / "evaluation.json").exists()
    assert (folder / "data-card.json").exists()
    assert (folder / "manifest.json").exists()


def test_category_and_price_inference_missing_unknown_and_known(trained):
    from app.ai.inference import category_suggestion, price_suggestion
    folder, report = trained
    known = dict(title="Wireless keyboard", description="Working electronic device with circuit battery cable and digital controls.", category="electronics", condition="good")
    category = category_suggestion(folder, known)
    assert category["value"] in (None, "electronics")
    price = price_suggestion(folder, known)
    if price["value"]:
        assert Decimal("0.01") <= Decimal(price["value"]) <= Decimal("9999999.99")
    assert category_suggestion(folder, {"title": "zxqv", "description": "zzxqv"})["value"] is None
    assert category_suggestion(folder / "missing", known)["value"] is None
    assert price_suggestion(folder / "missing", known)["value"] is None


def test_corrupt_artifact_abstains_without_loading_untrusted_payload(tmp_path, trained):
    import shutil
    from app.ai.inference import category_suggestion
    source, _ = trained
    shutil.copytree(source, tmp_path / "models")
    (tmp_path / "models" / "models.joblib").write_bytes(b"not a trusted model")
    result = category_suggestion(tmp_path / "models", {"title": "keyboard", "description": "electronic device"})
    assert result["value"] is None


def test_ai_endpoints_auth_csrf_and_no_silent_listing_update(db_app, user_factory, product_factory, trained):
    folder, _ = trained
    db_app.config.update(AI_FOLDER=str(folder), WTF_CSRF_ENABLED=False)
    client = db_app.test_client()
    assert client.post("/ai/category", data={}).status_code == 302
    user = user_factory()
    product = product_factory(seller=user, price=Decimal("45.00"))
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True
        session["login_at"] = 2000000000
    data = dict(title="Wireless keyboard", description="Working electronic device with digital controls.", category="electronics", condition="good")
    response = client.post("/ai/price", data=data)
    assert response.status_code == 200 and "message" in response.json
    from app.extensions import db
    db.session.refresh(product)
    assert product.price == Decimal("45.00")
    assert client.post("/ai/price", data={**data, "category": "bad"}).status_code == 400
    db_app.config["WTF_CSRF_ENABLED"] = True
    assert client.post("/ai/category", data=data).status_code == 400


def test_recommendations_visibility_fallback_and_determinism(db_app, user_factory, product_factory):
    from app.ai.recommendations import recommend
    viewer = user_factory()
    seller = user_factory()
    base = product_factory(seller=seller, title="Wireless keyboard", description="Electronic keyboard digital computer keys.")
    similar = product_factory(title="Computer keyboard", description="Digital electronic computer keyboard keys.")
    hidden = product_factory(seller=seller, status="archived")
    sold = product_factory(seller=seller, status="sold")
    own = product_factory(seller=viewer)
    result = recommend(viewer.id, base.id)
    ids = [row["id"] for row in result["items"]]
    assert similar.id in ids
    assert not {base.id, hidden.id, sold.id, own.id} & set(ids)
    assert result == recommend(viewer.id, base.id)
    assert len(ids) == len(set(ids)) <= 6


def test_recommendation_http_is_public_readonly_and_private_source_hidden(db_app, user_factory, product_factory):
    product = product_factory(status="archived")
    client = db_app.test_client()
    assert client.get("/recommendations").status_code == 200
    assert client.get(f"/recommendations?product_id={product.id}").status_code == 404


def test_price_metrics_match_manual_absolute_error_calculation(trained):
    from app.ai.data import prepare_dataset, synthetic_rows
    from app.ai.inference import load_bundle
    from app.ai.training import baseline_prices
    folder, report = trained
    test = prepare_dataset(synthetic_rows())['test']
    bundle, _ = load_bundle(folder)
    baseline = baseline_prices(test, bundle['medians'])
    manual = sum(abs(float(row['price']) - prediction) for row, prediction in zip(test, baseline)) / len(test)
    assert report['price']['baseline_mae'] == pytest.approx(manual)
    predictions = bundle['price'].predict(test) if bundle['price_method'] == 'ridge' else baseline
    selected = sum(abs(float(row['price']) - prediction) for row, prediction in zip(test, predictions)) / len(test)
    assert report['price']['mae'] == pytest.approx(selected)


def test_equal_similarity_uses_id_tie_breaker(db_app, product_factory):
    from datetime import datetime, timezone
    from app.ai.recommendations import build_index, recommend
    values = dict(title='Identical keyboard', description='Digital keyboard computer electronic keys and controls.')
    base = product_factory(**values)
    older = product_factory(**values, created_at=datetime(2025, 1, 1, tzinfo=timezone.utc))
    newer = product_factory(**values, created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    build_index(db_app.config['AI_FOLDER'])
    assert [item['id'] for item in recommend(None, base.id)['items']] == [older.id, newer.id]

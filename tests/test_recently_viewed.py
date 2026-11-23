"""MM-028 contracts for recent history and same-category products."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import re

import pytest
from sqlalchemy import inspect, select

from tests.test_marketplace import sign_in


@pytest.fixture()
def recent_web(db_app):
    db_app.config.update(WTF_CSRF_ENABLED=False,
                         SECRET_KEY="isolated-mm028-recent-secret")
    return db_app.test_client()


def section_html(response, identifier):
    html = response.get_data(as_text=True)
    match = re.search(
        rf'<section[^>]+id="{re.escape(identifier)}"[^>]*>(.*?)</section>',
        html, flags=re.DOTALL)
    return match.group(0) if match else ""


def card_ids(fragment):
    return [int(value) for value in re.findall(
        r'<a href="/products/(\d+)" class="photo-link">', fragment)]


def test_recent_model_has_composite_key_timestamp_and_ordering_index(db_app):
    from app.models import RecentProductView

    table = RecentProductView.__table__
    assert table.name == "recent_product_views"
    assert {column.name for column in table.primary_key.columns} == {
        "user_id", "product_id"}
    assert set(table.columns.keys()) == {"user_id", "product_id", "viewed_at"}
    assert not table.c.viewed_at.nullable
    assert any([column.name for column in index.columns][:2]
               == ["user_id", "viewed_at"] for index in table.indexes)
    with db_app.app_context():
        database_indexes = {item["name"] for item in inspect(
            db_app.extensions["sqlalchemy"].engine).get_indexes(table.name)}
    assert "ix_recent_product_views_user_viewed_at" in database_indexes


def test_active_view_records_history_without_personalization_analytics(
        recent_web, db_session, user_factory, product_factory):
    from app.models import InteractionEvent, RecentProductView

    seller = user_factory()
    buyer = user_factory(personalization=False)
    product = product_factory(seller=seller)
    sign_in(recent_web, buyer)

    assert recent_web.post(f"/products/{product.id}/view").status_code == 204
    row = db_session.get(RecentProductView, (buyer.id, product.id))
    assert row is not None and row.viewed_at.tzinfo is not None
    assert db_session.scalar(select(InteractionEvent).where(
        InteractionEvent.user_id == buyer.id)) is None


def test_repeat_and_sixth_views_keep_five_distinct_newest(
        recent_web, db_app, db_session, user_factory, product_factory):
    from app.models import RecentProductView

    seller = user_factory()
    buyer = user_factory(personalization=False)
    products = [product_factory(seller=seller, title=f"History item {index}")
                for index in range(6)]
    clock = [2_000_000_000.0]
    db_app.config["CLOCK"] = lambda: clock[0]
    sign_in(recent_web, buyer)
    for product in products:
        assert recent_web.post(f"/products/{product.id}/view").status_code == 204
        clock[0] += 1
    assert db_session.query(RecentProductView).filter_by(user_id=buyer.id).count() == 5

    assert recent_web.post(f"/products/{products[0].id}/view").status_code == 204
    rows = db_session.scalars(select(RecentProductView).where(
        RecentProductView.user_id == buyer.id).order_by(
            RecentProductView.viewed_at.desc(),
            RecentProductView.product_id.desc())).all()
    assert [row.product_id for row in rows] == [
        products[0].id, products[5].id, products[4].id,
        products[3].id, products[2].id]


def test_histories_are_isolated_between_users(
        recent_web, db_session, user_factory, product_factory):
    from app.models import RecentProductView

    seller = user_factory()
    first, second = user_factory(), user_factory()
    products = [product_factory(seller=seller) for _ in range(2)]
    sign_in(recent_web, first)
    recent_web.post(f"/products/{products[0].id}/view")
    sign_in(recent_web, second)
    recent_web.post(f"/products/{products[1].id}/view")

    pairs = set(db_session.execute(select(
        RecentProductView.user_id, RecentProductView.product_id)).all())
    assert pairs == {(first.id, products[0].id),
                     (second.id, products[1].id)}


@pytest.mark.parametrize("status", ["sold", "archived"])
def test_nonactive_view_is_rejected_and_not_stored(
        status, recent_web, db_session, user_factory, product_factory):
    from app.models import RecentProductView

    buyer = user_factory()
    product = product_factory(status=status)
    sign_in(recent_web, buyer)
    assert recent_web.post(f"/products/{product.id}/view").status_code == 404
    assert db_session.query(RecentProductView).count() == 0


def test_anonymous_view_is_login_protected_and_stores_nothing(
        recent_web, db_session, product_factory):
    from app.models import RecentProductView

    product = product_factory()
    assert recent_web.post(f"/products/{product.id}/view").status_code == 302
    assert db_session.query(RecentProductView).count() == 0


def test_explore_and_dashboard_render_same_active_recent_order(
        recent_web, db_session, user_factory, product_factory):
    from app.models import RecentProductView

    viewer = user_factory()
    seller = user_factory()
    old = product_factory(seller=seller, title="Old active")
    hidden = product_factory(seller=seller, title="Now sold", status="sold")
    newest = product_factory(seller=seller, title="Newest active")
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    db_session.add_all([
        RecentProductView(user_id=viewer.id, product_id=old.id,
                          viewed_at=start),
        RecentProductView(user_id=viewer.id, product_id=hidden.id,
                          viewed_at=start + timedelta(seconds=1)),
        RecentProductView(user_id=viewer.id, product_id=newest.id,
                          viewed_at=start + timedelta(seconds=2)),
    ])
    db_session.commit()
    sign_in(recent_web, viewer)

    explore = section_html(recent_web.get("/products"), "recently-viewed")
    dashboard = section_html(recent_web.get("/dashboard"), "recently-viewed")
    assert card_ids(explore) == card_ids(dashboard) == [newest.id, old.id]
    assert "Recently Viewed" in explore and "Recently Viewed" in dashboard
    assert hidden.title not in explore + dashboard


def test_recent_empty_state_is_private_and_ajax_does_not_duplicate_it(
        recent_web, user_factory):
    anonymous = recent_web.get("/products").get_data(as_text=True)
    assert 'id="recently-viewed"' not in anonymous
    viewer = user_factory()
    sign_in(recent_web, viewer)
    explore = recent_web.get("/products").get_data(as_text=True)
    dashboard = recent_web.get("/dashboard").get_data(as_text=True)
    assert "Products you open will appear here." in explore
    assert "Products you open will appear here." in dashboard
    search = recent_web.get("/products/search?q=camera").get_json()
    assert "recently-viewed" not in search["results_html"]
    assert "Recently Viewed" not in search["pagination_html"]


def test_active_authenticated_detail_has_view_marker_without_consent(
        recent_web, user_factory, product_factory):
    viewer = user_factory(personalization=False)
    active = product_factory()
    sold = product_factory(status="sold")
    sign_in(recent_web, viewer)
    active_html = recent_web.get(f"/products/{active.id}").get_data(as_text=True)
    sold_html = recent_web.get(f"/products/{sold.id}").get_data(as_text=True)
    assert f'data-view-url="/products/{active.id}/view"' in active_html
    assert "data-view-url" not in sold_html
    recent_web.get("/auth/logout")


def test_related_section_contains_three_distinct_active_same_category_items(
        recent_web, user_factory, product_factory):
    seller = user_factory()
    base = product_factory(seller=seller, category="electronics")
    eligible = [product_factory(seller=seller, category="electronics")
                for _ in range(5)]
    product_factory(seller=seller, category="electronics", status="sold")
    product_factory(seller=seller, category="electronics", status="archived")
    product_factory(seller=seller, category="books_media")

    related = section_html(
        recent_web.get(f"/products/{base.id}"), "related-products")
    identifiers = card_ids(related)
    assert len(identifiers) == len(set(identifiers)) == 3
    assert set(identifiers) <= {product.id for product in eligible}
    assert base.id not in identifiers
    assert "You might also like" in related


@pytest.mark.parametrize("alternative_count", [0, 1, 2])
def test_related_section_handles_small_candidate_sets(
        alternative_count, recent_web, user_factory, product_factory):
    seller = user_factory()
    base = product_factory(seller=seller, category="home_garden")
    alternatives = [product_factory(seller=seller, category="home_garden")
                    for _ in range(alternative_count)]
    related = section_html(
        recent_web.get(f"/products/{base.id}"), "related-products")
    if alternative_count == 0:
        assert related == ""
    else:
        assert len(card_ids(related)) == alternative_count
        assert set(card_ids(related)) == {product.id for product in alternatives}


def test_sold_base_can_show_active_same_category_alternatives(
        recent_web, user_factory, product_factory):
    seller = user_factory()
    base = product_factory(seller=seller, category="toys_games", status="sold")
    alternative = product_factory(seller=seller, category="toys_games")
    related = section_html(
        recent_web.get(f"/products/{base.id}"), "related-products")
    assert card_ids(related) == [alternative.id]


def test_product_related_is_server_rendered_but_dashboard_discover_more_remains(
        recent_web, user_factory, product_factory):
    viewer = user_factory()
    base = product_factory(category="electronics")
    product_factory(category="electronics")
    sign_in(recent_web, viewer)
    product_html = recent_web.get(f"/products/{base.id}").get_data(as_text=True)
    dashboard_html = recent_web.get("/dashboard").get_data(as_text=True)
    assert 'id="related-products"' in product_html
    assert 'id="recommendations"' not in product_html
    assert 'id="recommendations"' in dashboard_html


def test_static_view_post_and_template_contracts():
    root = Path(__file__).resolve().parents[1]
    script = (root / "app/static/js/market.js").read_text(encoding="utf-8")
    product = (root / "app/templates/product.html").read_text(encoding="utf-8")
    catalogue = (root / "app/templates/catalogue.html").read_text(encoding="utf-8")
    assert "credentials: 'same-origin'" in script
    assert "localStorage" not in script and "sessionStorage" not in script
    assert "related-products" in product
    assert "recommendations" not in product
    assert catalogue.index('id="recently-viewed"') < catalogue.index(
        'id="catalogue-search-form"')


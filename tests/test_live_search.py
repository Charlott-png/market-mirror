"""MM-020 contracts written before AJAX live-search implementation."""

from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from tests.test_marketplace import sign_in
from tests.test_seller_profile import Page


@pytest.fixture()
def live_web(db_app):
    """Use the real CSRF configuration because returned cart forms need tokens."""
    db_app.config.update(SECRET_KEY="isolated-live-search-test-secret")
    return db_app.test_client()


def fragment_page(client, html):
    response = client.application.response_class(html, status=200, mimetype="text/html")
    return Page(response)


def live_result(client, query_string=None):
    return client.get("/products/search", query_string=query_string)


def database_snapshot(db_session):
    from app.extensions import db
    return {table.name: tuple(db_session.execute(select(table)).all())
            for table in db.metadata.sorted_tables}


def test_live_endpoint_success_contract_and_no_store(live_web, user_factory, product_factory):
    seller = user_factory(username="ajax-seller")
    product = product_factory(seller=seller, title="AJAX study lamp")

    response = live_result(live_web)

    assert response.status_code == 200
    assert response.mimetype == "application/json"
    assert "no-store" in response.headers.get("Cache-Control", "")
    data = response.get_json()
    assert set(data) == {"results_html", "pagination_html", "total", "count_label",
                         "page", "pages", "canonical_query"}
    assert data["total"] == data["page"] == data["pages"] == 1
    assert data["count_label"] == "1 product"
    assert data["canonical_query"] == ""
    assert fragment_page(live_web, data["results_html"]).card_ids() == [product.id]
    assert data["pagination_html"] == ""


def test_explore_has_live_hooks_and_complete_form_fallback(live_web, user_factory, product_factory):
    product = product_factory(seller=user_factory(), title="Fallback desk lamp")
    page = Page(live_web.get("/products"))

    form = page.one("form", id="catalogue-search-form")
    assert form["attrs"]["method"].lower() == "get"
    assert form["attrs"]["action"] == "/products"
    assert form["attrs"]["data-live-search-url"] == "/products/search"
    assert page.one("input", id="q")["attrs"]["maxlength"] == "120"
    assert "Find products" in page.text("button", type="submit")
    feedback = page.one(id="live-search-feedback")
    assert feedback["attrs"]["role"] == "status"
    assert feedback["attrs"]["aria-live"] == "polite"
    assert feedback["attrs"]["aria-atomic"] == "true"
    assert page.one(id="live-search-spinner")["attrs"].get("aria-hidden") == "true"
    assert "hidden" in page.one(id="live-search-spinner")["attrs"]
    assert page.one(id="product-results")["attrs"]["aria-busy"] == "false"
    assert page.text(id="product-result-count") == "1 product"
    assert page.one(id="product-grid")
    assert page.one(id="product-pagination")
    assert product.id in page.card_ids(), "The server fallback must contain real initial results"


def test_private_catalogue_use_does_not_initialize_live_search(live_web, user_factory,
                                                                product_factory):
    seller = user_factory()
    product_factory(seller=seller)
    sign_in(live_web, seller)
    page = Page(live_web.get("/account/listings"))
    assert not page.find(id="catalogue-search-form")
    assert not page.find(id="live-search-feedback")
    assert not page.find(id="product-results")


def test_full_page_and_ajax_results_have_matching_ids_order_and_counts(
        live_web, user_factory, product_factory):
    seller = user_factory()
    product_factory(seller=seller, title="Alpha 100% lamp", description="Wood desk light",
                    category="home_garden", condition="good", price=Decimal("20.00"))
    product_factory(seller=seller, title="Beta chair", description="Alpha reading chair",
                    category="home_garden", condition="fair", price=Decimal("45.00"))
    product_factory(seller=seller, title="Gamma book", description="Literal underscore_name",
                    category="books_media", condition="like_new", price=Decimal("12.00"))

    queries = [
        {}, {"q": "Alpha"}, {"q": "%"}, {"q": "underscore_"},
        {"category": "home_garden"}, {"condition": "fair"},
        {"min_price": "15", "max_price": "30"}, {"sort": "price_asc"},
        {"sort": "price_desc"},
    ]
    for query in queries:
        full = Page(live_web.get("/products", query_string=query))
        response = live_result(live_web, query)
        assert response.status_code == 200, query
        data = response.get_json()
        ajax = fragment_page(live_web, data["results_html"])
        assert ajax.card_ids() == full.card_ids(), query
        assert data["total"] == len(full.card_ids()), query
        expected = f'{data["total"]} product' + ("" if data["total"] == 1 else "s")
        assert data["count_label"] == expected


@pytest.mark.parametrize("query,status", [
    ("q=a&q=b", 400),
    ("category=bad", 400),
    ("condition=bad", 400),
    ("sort=bad", 400),
    ("min_price=5&max_price=1", 400),
    ("min_price=not-money", 400),
    ("page=0", 400),
    ("page=-1", 400),
    ("page=x", 400),
    ("q=" + "x" * 121, 400),
])
def test_live_validation_uses_small_safe_json(live_web, query, status):
    response = live_result(live_web, query)
    assert response.status_code == status
    assert response.mimetype == "application/json"
    assert set(response.get_json()) == {"error"}
    body = response.get_data(as_text=True).lower()
    for forbidden in ("select ", "traceback", "sqlite", "c:\\", "/users/"):
        assert forbidden not in body


def test_canonical_query_is_validated_trimmed_and_allow_listed(live_web, user_factory,
                                                               product_factory):
    product_factory(seller=user_factory(), title="Lamp")
    response = live_result(
        live_web,
        "q=%20%20Lamp%20%20&category=home_garden&condition=good&sort=price_asc&unknown=secret&page=1",
    )
    assert response.status_code == 200
    canonical = response.get_json()["canonical_query"]
    parsed = parse_qs(canonical)
    assert parsed == {"q": ["Lamp"], "category": ["home_garden"],
                      "condition": ["good"], "sort": ["price_asc"]}
    assert "unknown" not in canonical and "secret" not in canonical and "page" not in canonical


def test_empty_unicode_and_length_boundary(live_web, user_factory, product_factory):
    seller = user_factory()
    product_factory(seller=seller, title="蓝色 laptop 😀")
    assert live_result(live_web, {"q": "   "}).status_code == 200
    unicode_response = live_result(live_web, {"q": "蓝色"})
    assert unicode_response.status_code == 200
    assert unicode_response.get_json()["total"] == 1
    assert live_result(live_web, {"q": "x" * 120}).status_code == 200
    assert live_result(live_web, {"q": "x" * 121}).status_code == 400


def test_visibility_escaping_and_private_canaries(live_web, user_factory, product_factory, caplog):
    seller = user_factory(username="private-seller", email="private-seller-canary@example.test")
    visible = product_factory(seller=seller, title='<script>alert("visible")</script> lamp')
    product_factory(seller=seller, status="sold", title="sold-live-search-canary")
    product_factory(seller=seller, status="archived", title="archived-live-search-canary")

    response = live_result(live_web)
    body = response.get_data(as_text=True)
    html = response.get_json()["results_html"]
    assert response.status_code == 200
    assert fragment_page(live_web, html).card_ids() == [visible.id]
    assert "&lt;script&gt;" in html and '<script>alert("visible")</script>' not in html
    for private in ("sold-live-search-canary", "archived-live-search-canary",
                    "private-seller-canary@example.test"):
        assert private not in body
        assert private not in caplog.text


def test_zero_results_clear_cards_and_pagination(live_web, user_factory, product_factory):
    product_factory(seller=user_factory(), title="Existing lamp")
    data = live_result(live_web, {"q": "definitely absent"}).get_json()
    page = fragment_page(live_web, data["results_html"])
    assert data["total"] == 0
    assert data["count_label"] == "0 products"
    assert data["pagination_html"] == ""
    assert page.card_ids() == []
    assert "No products found" in page.html
    assert "Existing lamp" not in page.html


def test_ajax_pagination_links_return_to_html_explore(live_web, user_factory, product_factory):
    seller = user_factory()
    for number in range(21):
        product_factory(seller=seller, title=f"Page item {number:02d}", price=Decimal(number + 1))
    data = live_result(live_web, {"sort": "price_asc"}).get_json()
    pagination = fragment_page(live_web, data["pagination_html"])
    links = [node["attrs"]["href"] for node in pagination.find("a")]
    assert data["total"] == 21 and data["pages"] == 2 and len(links) == 1
    assert links[0].startswith("/products?")
    assert "sort=price_asc" in links[0] and "page=2" in links[0]
    assert "/products/search" not in links[0]
    second = live_result(live_web, {"sort": "price_asc", "page": "2"}).get_json()
    assert len(fragment_page(live_web, second["results_html"]).card_ids()) == 1


def test_existing_seller_pagination_target_is_unchanged(live_web, user_factory, product_factory):
    seller = user_factory(username="paged-seller")
    for _ in range(21):
        product_factory(seller=seller)
    page = Page(live_web.get("/sellers/paged-seller"))
    assert page.one("nav", **{"class": "pagination"})
    anchors = [node["attrs"]["href"] for node in page.find("a")
               if "page=" in node["attrs"].get("href", "")]
    assert anchors and all(href.startswith("/sellers/paged-seller?") for href in anchors)


def test_fragments_keep_account_specific_cart_controls(live_web, user_factory, product_factory):
    seller = user_factory(username="card-owner")
    buyer = user_factory(username="card-buyer")
    product = product_factory(seller=seller, title="Shared card lamp")

    anonymous = live_result(live_web).get_json()["results_html"]
    assert "Sign in to add to cart" in anonymous

    sign_in(live_web, buyer)
    buyer_response = live_result(live_web)
    buyer_html = buyer_response.get_json()["results_html"]
    buyer_page = fragment_page(live_web, buyer_html)
    add_form = buyer_page.one("form", action=f"/cart/items/{product.id}")
    assert add_form["attrs"]["method"].lower() == "post"
    assert 'name="csrf_token"' in buyer_html
    assert "no-store" in buyer_response.headers.get("Cache-Control", "")

    sign_in(live_web, seller)
    owner_html = live_result(live_web).get_json()["results_html"]
    assert "Your listing" in owner_html
    assert f'action="/cart/items/{product.id}"' not in owner_html


def test_live_search_is_read_only_and_non_get_cannot_mutate(live_web, user_factory,
                                                             product_factory, db_session):
    product_factory(seller=user_factory(), title="Read-only lamp")
    before = database_snapshot(db_session)
    assert live_result(live_web, {"q": "lamp"}).status_code == 200
    after_get = database_snapshot(db_session)
    response = live_web.post("/products/search", data={"q": "lamp"})
    after_post = database_snapshot(db_session)
    assert response.status_code in {400, 405}
    assert before == after_get == after_post


def test_unexpected_database_failure_is_safe(live_web, monkeypatch):
    from app.extensions import db

    def fail(*_args, **_kwargs):
        raise OperationalError("SELECT private_table FROM C:\\secret\\database", {}, Exception("secret"))

    monkeypatch.setattr(db.session, "scalar", fail)
    response = live_result(live_web, {"q": "private-query-canary"})
    assert response.status_code == 503
    body = response.get_data(as_text=True)
    assert "private-query-canary" not in body
    assert "private_table" not in body and "C:\\secret" not in body


def test_live_search_javascript_and_css_contracts():
    root = Path(__file__).parents[1]
    script = (root / "app" / "static" / "js" / "market.js").read_text(encoding="utf-8")
    styles = (root / "app" / "static" / "css" / "style.css").read_text(encoding="utf-8")

    for token in ("catalogue-search-form", "300", "setTimeout", "compositionstart",
                  "compositionend", "AbortController", "requestSequence",
                  "history.replaceState", "aria-busy", "Live search is unavailable"):
        assert token in script
    for token in (".live-search-feedback", ".live-search-spinner",
                  "@keyframes live-search-spin", "prefers-reduced-motion"):
        assert token in styles
    assert ".live-search-spinner[hidden]" in styles


"""MM-021 contracts written before the mobile-navigation implementation."""

from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import func, select

from tests.test_cart import csrf_for
from tests.test_marketplace import sign_in
from tests.test_seller_profile import Page


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def mobile_web(db_app):
    """Use the real CSRF protection with a test-owned database."""
    db_app.config.update(SECRET_KEY="isolated-mobile-navigation-secret")
    return db_app.test_client()


def mobile_items(page):
    return page.find("a", **{"class": "mobile-navigation-item"})


def current_mobile_label(page):
    current = page.find("a", **{"aria-current": "page"})
    current = [node for node in current if "mobile-navigation-item" in node["attrs"].get("class", "").split()]
    assert len(current) <= 1
    return " ".join(current[0]["text"].split()) if current else None


@pytest.mark.parametrize(("endpoint", "expected"), [
    ("main.home", "home"),
    ("market.browse", "explore"),
    ("market.detail", "explore"),
    ("market.seller_profile", "explore"),
    ("market.create_listing", "sell"),
    ("market.edit_listing", "sell"),
    ("market.preview", "sell"),
    ("market.own_listings", "sell"),
    ("engagement.inbox", "messages"),
    ("engagement.thread", "messages"),
    ("auth.profile", "profile"),
    ("engagement.dashboard", "profile"),
    ("engagement.saved", "profile"),
    ("cart.review", "profile"),
    ("auth.login", None),
    ("auth.logout", None),
    ("market.live_search", None),
    ("cart.add", None),
    (None, None),
    ("unknown.endpoint", None),
])
def test_exact_endpoint_group_mapping(endpoint, expected):
    from app.navigation import mobile_nav_section

    assert mobile_nav_section(endpoint) == expected


def test_base_contains_five_labelled_inline_icon_links_in_order(mobile_web):
    page = Page(mobile_web.get("/"))
    page.one("nav", **{"class": "desktop-navigation", "aria-label": "Main navigation"})
    page.one("nav", **{"class": "mobile-navigation", "aria-label": "Mobile navigation"})
    items = mobile_items(page)
    assert [" ".join(item["text"].split()) for item in items] == [
        "Home", "Explore", "Sell", "Messages", "Profile",
    ]
    assert [item["attrs"]["href"] for item in items] == [
        "/", "/products", "/listings/new", "/messages", "/account/profile",
    ]
    icons = page.find("svg", **{"class": "mobile-navigation-icon"})
    labels = page.find("span", **{"class": "mobile-navigation-label"})
    assert len(icons) == len(labels) == 5
    for icon in icons:
        assert icon["attrs"]["aria-hidden"] == "true"
        assert icon["attrs"]["focusable"] == "false"
        assert icon["attrs"]["viewbox"] == "0 0 24 24"
    assert all(not urlsplit(item["attrs"]["href"]).netloc for item in items)
    assert all(not item["attrs"]["href"].lower().startswith("javascript:") for item in items)


def test_representative_pages_mark_exactly_one_correct_item(mobile_web, user_factory):
    assert current_mobile_label(Page(mobile_web.get("/"))) == "Home"
    assert current_mobile_label(Page(mobile_web.get("/products"))) == "Explore"
    assert current_mobile_label(Page(mobile_web.get("/auth/login"))) is None

    user = user_factory()
    sign_in(mobile_web, user)
    for path, label in [
        ("/listings/new", "Sell"),
        ("/messages", "Messages"),
        ("/account/profile", "Profile"),
        ("/dashboard", "Profile"),
        ("/saved", "Profile"),
        ("/cart", "Profile"),
    ]:
        assert current_mobile_label(Page(mobile_web.get(path))) == label


@pytest.mark.parametrize("path", ["/listings/new", "/messages", "/account/profile"])
def test_anonymous_protected_mobile_destinations_keep_a_local_next_value(
        mobile_web, db_session, path):
    from app.models import CartItem, Product, User

    before = tuple(db_session.scalar(select(func.count()).select_from(model))
                   for model in (User, Product, CartItem))
    response = mobile_web.get(path)
    assert response.status_code == 302
    location = urlsplit(response.location)
    assert location.path == "/auth/login"
    assert parse_qs(location.query)["next"] == [path]
    assert location.netloc == ""
    after = tuple(db_session.scalar(select(func.count()).select_from(model))
                  for model in (User, Product, CartItem))
    assert after == before


def test_signed_in_mobile_destinations_are_reachable(mobile_web, user_factory):
    sign_in(mobile_web, user_factory())
    for path in ("/", "/products", "/listings/new", "/messages", "/account/profile"):
        assert mobile_web.get(path).status_code == 200


def test_profile_alone_contains_mobile_account_shortcuts(mobile_web, user_factory):
    user = user_factory()
    sign_in(mobile_web, user)
    profile = Page(mobile_web.get("/account/profile"))
    shortcuts = profile.one("section", id="mobile-account-shortcuts")
    assert "Account shortcuts" in shortcuts["text"]
    assert profile.find("a", href="/dashboard")
    assert profile.find("a", href="/saved")
    profile.one("a", id="mobile-account-cart", href="/cart", **{"data-cart-count": "0"})
    assert "Cart 0" in profile.text(id="mobile-account-cart")
    profile.one("form", action="/auth/logout", method="post", **{"class": "mobile-account-logout"})

    for path in ("/auth/login", "/auth/register", "/listings/new"):
        assert not Page(mobile_web.get(path)).find(id="mobile-account-shortcuts")


def test_profile_shortcut_cart_count_is_current_user_only(
        mobile_web, user_factory, product_factory, db_session):
    from app.models import CartItem

    buyer, empty_buyer, seller = user_factory(), user_factory(), user_factory()
    products = [product_factory(seller=seller) for _ in range(12)]
    db_session.add_all([CartItem(user_id=buyer.id, product_id=product.id) for product in products])
    db_session.commit()

    sign_in(mobile_web, buyer)
    full = Page(mobile_web.get("/account/profile"))
    assert full.one(id="mobile-account-cart")["attrs"]["data-cart-count"] == "12"
    assert full.text(id="mobile-account-cart") == "Cart 12"

    sign_in(mobile_web, empty_buyer)
    empty = Page(mobile_web.get("/account/profile"))
    assert empty.one(id="mobile-account-cart")["attrs"]["data-cart-count"] == "0"
    assert buyer.email not in empty.html


def test_mobile_logout_remains_post_only_csrf_protected_and_clears_session(
        mobile_web, user_factory):
    sign_in(mobile_web, user_factory())
    html = mobile_web.get("/account/profile").get_data(as_text=True)
    token = csrf_for(html, "/auth/logout")
    assert mobile_web.get("/auth/logout").status_code == 405
    assert mobile_web.post("/auth/logout").status_code == 400
    assert mobile_web.post("/auth/logout", data={"csrf_token": "not-valid"}).status_code == 400
    valid = mobile_web.post("/auth/logout", data={"csrf_token": token})
    assert valid.status_code == 302 and urlsplit(valid.location).path == "/"
    assert mobile_web.get("/account/profile").status_code == 302


def test_existing_authenticated_desktop_navigation_is_preserved(mobile_web, user_factory):
    sign_in(mobile_web, user_factory())
    page = Page(mobile_web.get("/"))
    desktop = page.one("nav", **{"class": "desktop-navigation", "aria-label": "Main navigation"})
    for label in ("Home", "Explore", "Dashboard", "Saved", "Messages", "Cart", "Profile", "Sign out"):
        assert label in desktop["text"]
    page.one(id="cart-navigation-link")


def css_blocks(css, selector):
    return re.findall(rf"{re.escape(selector)}\s*\{{([^}}]*)\}}", css, flags=re.S)


def test_responsive_css_contract_reserves_space_and_prevents_overflow():
    css = (PROJECT_ROOT / "app/static/css/style.css").read_text(encoding="utf-8")
    assert re.search(r"\.mobile-navigation\s*\{\s*display:\s*none", css)
    assert re.search(r"\.mobile-account-shortcuts\s*\{\s*display:\s*none", css)
    mobile = re.search(r"@media\s*\(max-width:\s*42rem\)\s*\{(?P<body>.*?)\n\}", css, re.S)
    assert mobile, "The approved 42rem mobile breakpoint is missing"
    body = mobile.group("body")
    assert re.search(r"\.desktop-navigation\s*\{[^}]*display:\s*none", body, re.S)
    assert re.search(r"\.mobile-navigation\s*\{[^}]*display:\s*grid", body, re.S)
    assert re.search(r"\.mobile-navigation\s*\{[^}]*position:\s*fixed", body, re.S)
    assert "repeat(5, minmax(0, 1fr))" in body
    assert re.search(r"\.mobile-navigation-item\s*\{[^}]*min-height:\s*44px", body, re.S)
    assert re.search(r"\.mobile-navigation-item\s*\{[^}]*min-width:\s*0", body, re.S)
    assert re.search(r"\.mobile-account-shortcuts\s*\{[^}]*display:", body, re.S)
    assert body.count("env(safe-area-inset-bottom)") >= 2
    assert re.search(r"\[aria-current=[\"']page[\"']\]\s*\{[^}]*(font-weight|border|box-shadow)", body, re.S)
    assert ":focus-visible" in css


def test_print_and_no_javascript_contracts():
    css = (PROJECT_ROOT / "app/static/css/style.css").read_text(encoding="utf-8")
    script = (PROJECT_ROOT / "app/static/js/market.js").read_text(encoding="utf-8")
    printed = re.search(r"@media\s+print\s*\{(?P<body>.*?)\n\}", css, re.S)
    assert printed
    assert ".mobile-navigation" in printed.group("body")
    assert ".mobile-account-shortcuts" in printed.group("body")
    assert "padding-bottom: 0 !important" in printed.group("body")
    assert "mobile-navigation" not in script
    assert "mobile-account-shortcuts" not in script


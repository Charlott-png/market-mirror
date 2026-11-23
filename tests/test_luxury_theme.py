"""MM-030 Midnight & Gold visual contracts, written before implementation.

These tests deliberately check durable design and safety boundaries. They do
not pretend that string inspection replaces the final browser review.
"""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
STYLE_PATH = ROOT / "app" / "static" / "css" / "style.css"
BASE_PATH = ROOT / "app" / "templates" / "base.html"
CATALOGUE_PATH = ROOT / "app" / "templates" / "catalogue.html"
MACROS_PATH = ROOT / "app" / "templates" / "macros.html"


def read(path):
    return path.read_text(encoding="utf-8")


def compact(value):
    return re.sub(r"\s+", " ", value).strip().lower()


def rule(css, selector):
    """Return all declaration bodies whose selector text contains selector."""
    bodies = []
    for match in re.finditer(r"(?P<selectors>[^{}]+)\{(?P<body>[^{}]*)\}", css):
        if selector in match.group("selectors"):
            bodies.append(compact(match.group("body")))
    return " ".join(bodies)


def test_approved_midnight_gold_tokens_are_named_exactly():
    css = read(STYLE_PATH).lower()
    expected = {
        "--midnight": "#0a1128",
        "--deepest": "#05070d",
        "--raised": "#121b33",
        "--glass": "rgb(18 27 51 / 82%)",
        "--gold": "#d4af37",
        "--gold-bright": "#f1d77a",
        "--gold-dark": "#9a7514",
        "--off-white": "#f7f3e8",
        "--cream-muted": "#c9c1ae",
        "--gold-line": "rgb(212 175 55 / 35%)",
        "--error": "#ffb4b4",
        "--success": "#a8e6b0",
    }
    for name, value in expected.items():
        assert re.search(rf"{re.escape(name)}\s*:\s*{re.escape(value)}\s*;", css), name
    assert "color-scheme: dark" in css
    assert "color-scheme: light dark" not in css


def test_typography_uses_approved_display_and_body_fallbacks():
    css = read(STYLE_PATH)
    lowered = css.lower()
    assert '--font-display: "Cinzel", Georgia, "Times New Roman", serif;' in css
    assert '--font-body: "Montserrat", Arial, Helvetica, sans-serif;' in css
    assert "font-family: var(--font-body)" in rule(css, "body")
    heading_rules = " ".join(rule(css, selector) for selector in ("h1", "h2", ".brand"))
    assert "font-family: var(--font-display)" in heading_rules
    assert "arial, helvetica, sans-serif" in lowered


def test_base_loads_fonts_privately_and_updates_stylesheet_cache_key():
    base = read(BASE_PATH)
    lowered = base.lower()
    assert 'rel="preconnect" href="https://fonts.googleapis.com"' in lowered
    assert 'rel="preconnect" href="https://fonts.gstatic.com" crossorigin' in lowered
    font_links = re.findall(r'<link[^>]+href="([^"]+)"[^>]*>', base)
    google_stylesheets = [url for url in font_links if "fonts.googleapis.com/css2" in url]
    assert len(google_stylesheets) == 1
    font_url = google_stylesheets[0].lower()
    assert "cinzel" in font_url and "montserrat" in font_url and "display=swap" in font_url
    assert not re.search(r'<script[^>]+(?:google|font)', lowered)
    assert "v='mm030-midnight-gold'" in base


def test_header_is_sticky_dark_and_has_gold_interaction_states():
    css = read(STYLE_PATH)
    header = rule(css, ".site-header")
    assert "position: sticky" in header
    assert "top: 0" in header
    assert "z-index:" in header
    assert "var(--deepest)" in header or "var(--midnight)" in header
    assert "var(--gold-line)" in header
    assert "backdrop-filter" in css
    nav_states = rule(css, ".desktop-navigation a:hover") + rule(css, ".desktop-navigation a:focus-visible")
    assert "var(--gold-bright)" in nav_states
    assert "underline" in nav_states or "border" in nav_states


def test_footer_is_deep_black_gold_and_print_safe():
    css = read(STYLE_PATH)
    footer = rule(css, ".site-footer")
    assert "var(--deepest)" in footer
    assert "var(--gold-line)" in footer
    assert "var(--gold)" in footer or "var(--cream-muted)" in footer
    print_section = re.search(r"@media\s+print\s*\{(?P<body>.*)\}\s*$", css, re.S)
    assert print_section
    assert ".site-footer" in print_section.group("body")
    assert "background" in print_section.group("body")


def test_product_cards_have_fallback_glass_border_and_shadow():
    css = read(STYLE_PATH)
    card = rule(css, ".card")
    assert "var(--raised)" in card
    assert "var(--gold-line)" in card
    assert "box-shadow" in card
    assert "var(--glass)" in css
    assert re.search(r"@supports\s*\([^)]*backdrop-filter", css)
    assert "backdrop-filter" in css
    assert "border" in rule(css, ".card img") or "border" in rule(css, ".photo-link")


def test_card_hover_is_pointer_only_and_reduced_motion_safe():
    css = read(STYLE_PATH)
    hover_sections = re.findall(
        r"@media\s*\(hover:\s*hover\)\s*and\s*\(pointer:\s*fine\)\s*\{(?P<body>.*?)\n\}",
        css,
        re.S,
    )
    assert any(".card:hover" in section for section in hover_sections)
    reduced_sections = re.findall(
        r"@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{(?P<body>.*?)\n\}",
        css,
        re.S,
    )
    assert any(".card" in section and "transition" in section for section in reduced_sections)


def test_card_hierarchy_and_gold_add_to_cart_bar_are_complete():
    css = read(STYLE_PATH)
    assert "var(--gold-bright)" in rule(css, ".price")
    assert "var(--cream-muted)" in rule(css, ".tag")
    cart_form = rule(css, ".cart-add-form")
    cart_button = rule(css, ".cart-add-form button")
    assert "width: 100%" in cart_form
    assert "width: 100%" in cart_button
    assert "var(--gold)" in cart_button
    assert "var(--midnight)" in cart_button
    assert "var(--gold-bright)" in rule(css, ".cart-add-form button:hover")
    assert "var(--gold-dark)" in rule(css, ".cart-add-form button:active")
    assert "not-allowed" in rule(css, ".cart-add-form button:disabled")
    assert "outline" in rule(css, ".cart-add-form button:focus-visible")


def test_explore_has_scoped_hooks_spacing_and_preserved_ajax_ids():
    template = read(CATALOGUE_PATH)
    assert 'class="catalogue-page"' in template
    assert 'class="recently-viewed-section"' in template
    for element_id in (
        "catalogue-search-form",
        "live-search-feedback",
        "live-search-spinner",
        "live-search-status",
        "product-result-count",
        "product-results",
        "product-grid",
        "product-pagination",
    ):
        assert template.count(f'id="{element_id}"') == 1
    css = read(STYLE_PATH)
    explore_grid = rule(css, ".catalogue-page #product-grid")
    assert re.search(r"gap:\s*(?:1\.75|1\.8|1\.875|2)rem", explore_grid)
    assert "grid-template-columns: 1fr" in css


def test_controls_forms_autofill_feedback_and_upload_use_theme_tokens():
    css = read(STYLE_PATH)
    assert "var(--gold)" in rule(css, "button")
    assert "var(--midnight)" in rule(css, "button")
    assert "var(--gold-bright)" in rule(css, "button:hover")
    assert "var(--gold-dark)" in rule(css, "button:active")
    assert "var(--gold)" in rule(css, ".secondary")
    assert "not-allowed" in rule(css, "button:disabled")
    fields = rule(css, "input:not") + rule(css, "textarea") + rule(css, "select")
    assert "var(--raised)" in fields and "var(--off-white)" in fields
    assert "::placeholder" in css and "var(--cream-muted)" in rule(css, "::placeholder")
    assert ":-webkit-autofill" in css
    assert "var(--gold-bright)" in rule(css, ".image-dropzone.is-drag-over")
    assert "var(--error)" in rule(css, ".error-text")
    assert "var(--success)" in css


def test_gallery_cart_seller_order_chat_and_assistant_are_themed():
    css = read(STYLE_PATH)
    expected_tokens = {
        ".product-gallery-thumbnail[aria-current=\"true\"]": "var(--gold)",
        ".image-lightbox-close": "var(--gold)",
        ".cart-summary": "var(--raised)",
        ".cart-unavailable": "dashed",
        ".seller-activity-badge": "var(--gold)",
        ".order-receipt": "var(--gold-line)",
        ".chat-message--outgoing .chat-bubble": "var(--gold-line)",
        ".chat-message--incoming .chat-bubble": "var(--raised)",
        ".shop-assistant-launcher": "var(--gold)",
        ".shop-assistant-panel": "var(--gold-line)",
        ".mobile-navigation-item[aria-current=\"page\"]": "var(--gold-bright)",
    }
    for selector, token in expected_tokens.items():
        assert token in rule(css, selector), selector


def test_responsive_motion_forced_color_and_print_boundaries_exist():
    css = read(STYLE_PATH)
    assert re.search(r"@media\s*\(max-width:\s*42rem\)", css)
    assert re.search(r"@media\s*\(max-width:\s*30rem\)", css)
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "@media (forced-colors: active)" in css
    assert "@media print" in css
    assert "min-height: 44px" in rule(css, ".mobile-navigation-item")


def test_critical_forms_and_javascript_hooks_are_preserved():
    macros = read(MACROS_PATH)
    catalogue = read(CATALOGUE_PATH)
    base = read(BASE_PATH)
    assert 'class="cart-add-form" method="post"' in macros
    assert "url_for('cart.add', product_id=product.id)" in macros
    assert "{{ csrf_field() }}" in macros
    assert 'name="next"' in macros
    assert 'method="get"' in catalogue
    assert 'data-live-search-url=' in catalogue
    assert 'id="cart-navigation-link"' in base
    assert 'class="mobile-navigation"' in base
    assert "{% include '_shop_assistant.html' %}" in base
    assert 'filename=\'js/market.js\'' in base
    assert 'filename=\'js/shop-assistant.js\'' in base


def test_theme_does_not_add_inline_handlers_or_external_javascript():
    templates = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "app" / "templates").rglob("*.html")
    )
    assert not re.search(r"\son(?:click|change|input|submit|load|error)\s*=", templates, re.I)
    sources = re.findall(r'<script[^>]+src="([^"]+)"', templates, re.I)
    assert sources
    assert all("url_for('static'" in source for source in sources)

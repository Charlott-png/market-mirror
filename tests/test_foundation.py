"""Tests derived from the approved MM-001 Project Foundation specification."""

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_application_can_be_created_in_testing_mode(app):
    """TEST-001: The application factory accepts a testing configuration."""
    assert app.config["TESTING"] is True


def test_home_page_returns_successful_html(client):
    """TEST-002 / AC-001: The home page explains the project."""
    response = client.get("/")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert response.content_type.startswith("text/html")
    assert "Market Mirror" in page
    assert "online marketplace" in page.lower()
    assert "added gradually" in page.lower()


def test_health_endpoint_returns_exact_public_contract(client):
    """TEST-003 / AC-002: Health JSON contains only approved public fields."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.content_type.startswith("application/json")
    assert response.get_json() == {
        "service": "market-mirror",
        "status": "ok",
    }


def test_unknown_route_returns_custom_404_page(client):
    """TEST-004 / AC-003: Missing URLs return a useful HTML error page."""
    response = client.get("/this-page-does-not-exist")
    page = response.get_data(as_text=True)

    assert response.status_code == 404
    assert response.content_type.startswith("text/html")
    assert "not found" in page.lower()
    assert 'href="/"' in page or "href='/'" in page


def test_home_page_contains_shared_layout_elements(client):
    """TEST-005 / AC-004: The home page contains accessible base structure."""
    response = client.get("/")
    page = response.get_data(as_text=True).lower()

    assert '<html lang="en"' in page
    assert 'name="viewport"' in page
    assert "<header" in page
    assert "<main" in page
    assert "<footer" in page


def test_404_page_contains_shared_layout_elements(client):
    """TEST-006 / AC-004: The 404 page uses the shared site layout."""
    response = client.get("/missing-page")
    page = response.get_data(as_text=True).lower()

    assert response.status_code == 404
    assert "<header" in page
    assert "<main" in page
    assert "<footer" in page


def test_stylesheet_is_linked_and_available(client):
    """TEST-007: The page links to a CSS file served by Flask."""
    home_response = client.get("/")
    page = home_response.get_data(as_text=True)
    stylesheet_match = re.search(
        r'<link[^>]+href=["\']([^"\']+\.css(?:\?[^"\']*)?)["\']',
        page,
        flags=re.IGNORECASE,
    )

    assert stylesheet_match is not None, "The home page must link to a CSS file."

    stylesheet_response = client.get(stylesheet_match.group(1))
    assert stylesheet_response.status_code == 200
    assert stylesheet_response.content_type.startswith("text/css")


def test_dependency_files_contain_correct_package_groups():
    """TEST-008: Runtime and development dependencies remain separate."""
    runtime_path = PROJECT_ROOT / "requirements.txt"
    development_path = PROJECT_ROOT / "requirements-dev.txt"

    assert runtime_path.exists(), "requirements.txt has not been created yet."
    assert development_path.exists(), "requirements-dev.txt has not been created yet."

    runtime_requirements = runtime_path.read_text(encoding="utf-8").lower()
    development_requirements = development_path.read_text(encoding="utf-8").lower()

    assert re.search(r"^flask(?:[<>=!~].*)?$", runtime_requirements, re.MULTILINE)
    assert not re.search(r"^pytest(?:[<>=!~].*)?$", runtime_requirements, re.MULTILINE)
    assert re.search(r"^pytest(?:[<>=!~].*)?$", development_requirements, re.MULTILINE)


def test_readme_contains_required_setup_guidance():
    """TEST-009: A beginner can find every required setup step in the README."""
    readme_path = PROJECT_ROOT / "README.md"

    assert readme_path.exists(), "README.md has not been created yet."

    readme = readme_path.read_text(encoding="utf-8").lower()
    required_guidance = (
        "prerequisites",
        "virtual environment",
        "activate",
        "install",
        "run",
        "test",
        "not implemented",
    )

    for phrase in required_guidance:
        assert phrase in readme, f"README.md must explain: {phrase}"


"""MM-002 regression guard for the completed MM-001 public contracts."""


def test_mm001_public_contracts_remain_unchanged(client):
    """TEST-REG-001 / AC-DB-011: database integration preserves MM-001."""
    home = client.get("/")
    health = client.get("/health")
    missing = client.get("/still-not-a-real-page")

    assert home.status_code == 200
    assert "Market Mirror" in home.get_data(as_text=True)
    assert health.status_code == 200
    assert health.get_json() == {"service": "market-mirror", "status": "ok"}
    assert missing.status_code == 404

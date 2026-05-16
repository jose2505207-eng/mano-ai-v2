"""Tests for health and sponsor-status endpoints."""


def test_health_endpoint(client):
    """GET /api/health returns 200 with expected payload."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"ok": True, "app": "Mano AI", "mode": "real-web-agent"}


def test_sponsor_status_endpoint(client):
    """GET /api/sponsor-status returns 200 with sponsors list."""
    resp = client.get("/api/sponsor-status")
    assert resp.status_code == 200
    data = resp.json()
    assert "sponsors" in data
    sponsors = data["sponsors"]
    assert len(sponsors) == 10


def test_sponsor_status_fields(client):
    """Each sponsor has name, status, and details fields."""
    resp = client.get("/api/sponsor-status")
    sponsors = resp.json()["sponsors"]
    for sponsor in sponsors:
        assert "name" in sponsor, f"Missing 'name' in {sponsor}"
        assert "status" in sponsor, f"Missing 'status' in {sponsor}"
        assert "details" in sponsor, f"Missing 'details' in {sponsor}"
        assert sponsor["status"] in ("connected", "not_configured")

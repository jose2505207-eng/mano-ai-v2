"""Tests for task, profile, and logs API endpoints."""


def test_create_task(client):
    """POST /api/tasks returns 200 with task_id and status."""
    resp = client.post("/api/tasks", json={"task": "Search for flights to LA"})
    assert resp.status_code == 200
    data = resp.json()
    assert "task_id" in data
    assert "status" in data
    assert data["status"] in ("running", "waiting_for_user", "waiting_for_approval", "done", "stuck", "failed")


def test_get_nonexistent_task(client):
    """GET /api/tasks/{nonexistent} returns 404."""
    resp = client.get("/api/tasks/nonexistent-id-123")
    assert resp.status_code == 404


def test_get_profile(client):
    """GET /api/profile returns valid profile."""
    resp = client.get("/api/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert "preferred_language" in data
    assert "payment_allowed" in data


def test_update_profile(client, sample_profile):
    """POST /api/profile updates profile."""
    resp = client.post("/api/profile", json=sample_profile)
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Jose Ivan Zaragoza"
    assert data["email"] == "jose@example.com"


def test_get_logs(client):
    """GET /api/logs returns logs array."""
    resp = client.get("/api/logs")
    assert resp.status_code == 200
    data = resp.json()
    assert "logs" in data
    assert isinstance(data["logs"], list)

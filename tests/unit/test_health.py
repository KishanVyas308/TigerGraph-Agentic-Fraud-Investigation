"""Unit tests for FastAPI health check and root endpoints."""

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_health_check_endpoint():
    """Verify GET /health returns 200 and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "app_name" in data
    assert "version" in data
    assert "timestamp" in data


def test_root_endpoint():
    """Verify GET / returns 200 and links to health and docs."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Welcome to" in data["message"]
    assert data["health_url"] == "/health"
    assert data["docs_url"] == "/docs"

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_root_returns_service_information() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "ClauseIQ"
    assert response.json()["status"] == "running"


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

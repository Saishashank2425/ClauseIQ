from fastapi.testclient import TestClient
from backend.app.main import app


def test_demo_endpoint_returns_synthetic_contract():
    response = TestClient(app).get("/api/v1/demo")
    assert response.status_code == 200
    data = response.json()
    assert data["filename"].endswith("_DEMO.docx")
    assert len(data["clauses"]) >= 5
    assert data["summary"]["high"] == 1


def test_demo_question_returns_retrieved_evidence():
    response = TestClient(app).post(
        "/api/v1/demo/ask",
        json={"question": "What does the indemnification clause say about liability limits?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["evidence"]
    assert data["evidence"][0]["clause_id"] == "C0001"

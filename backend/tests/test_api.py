from io import BytesIO
from docx import Document
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.api.auth import require_user


def make_docx():
    doc = Document()
    doc.add_paragraph("1. LIABILITY")
    doc.add_paragraph("The supplier has unlimited liability for all claims under this agreement.")
    out = BytesIO()
    doc.save(out)
    return out.getvalue()


def test_analyze_endpoint_accepts_docx_for_authenticated_user():
    app.dependency_overrides[require_user] = lambda: {"id": "test-user", "email": "test@example.com"}
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/analyze",
            files={"file": ("contract.docx", make_docx(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "contract.docx"
        assert data["summary"]["high"] >= 1
    finally:
        app.dependency_overrides.clear()


def test_analyze_endpoint_requires_authentication():
    client = TestClient(app)
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("contract.docx", make_docx(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 401

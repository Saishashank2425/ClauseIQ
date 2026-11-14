from io import BytesIO
from docx import Document
from fastapi.testclient import TestClient
from backend.app.main import app

def make_docx():
    doc=Document()
    doc.add_paragraph("1. LIABILITY")
    doc.add_paragraph("The supplier has unlimited liability for all claims under this agreement.")
    out=BytesIO();doc.save(out);return out.getvalue()

def test_analyze_endpoint_accepts_docx():
    client=TestClient(app)
    response=client.post("/api/v1/analyze",files={"file":("contract.docx",make_docx(),"application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    assert response.status_code==200
    data=response.json()
    assert data["filename"]=="contract.docx"
    assert data["summary"]["high"]>=1

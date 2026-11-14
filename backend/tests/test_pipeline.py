from io import BytesIO
from docx import Document
from backend.app.services.analyzer import analyze_document
from backend.app.preprocessing.segment import segment_pages
from backend.app.ingestion.extract import ExtractedPage
from backend.app.risk.rules import assess_clause


def test_risk_rules_are_transparent():
    risk, flags, explanation = assess_clause("The supplier has unlimited liability for all claims.")
    assert risk == "high"
    assert "unlimited_liability" in flags
    assert "unlimited_liability" in explanation


def test_segmentation_preserves_page_provenance():
    pages = [ExtractedPage(3, "1. PAYMENT TERMS\\nThe customer shall pay all invoices within thirty days.\\n\\n2. TERM\\nThis agreement automatically renews for one year.")]
    clauses = segment_pages(pages)
    assert clauses
    assert all(c.page == 3 for c in clauses)


def test_docx_analysis_smoke():
    doc = Document()
    doc.add_paragraph("1. LIMITATION OF LIABILITY")
    doc.add_paragraph("The supplier has unlimited liability for all claims arising under this agreement.")
    stream = BytesIO()
    doc.save(stream)
    result = analyze_document("sample.docx", stream.getvalue())
    assert result.word_count > 0
    assert result.summary["high"] >= 1

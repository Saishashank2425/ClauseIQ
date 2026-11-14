from backend.app.ingestion.extract import ExtractedPage
from backend.app.preprocessing.segment import segment_pages

def test_paragraph_segmentation_splits_real_newlines():
    text=("1. PAYMENT\nThe buyer shall pay all invoices within thirty days of receipt.\n\n"
          "2. TERMINATION\nEither party may terminate this agreement upon thirty days written notice.")
    clauses=segment_pages([ExtractedPage(page=2,text=text)])
    assert len(clauses)>=2
    assert all(c.page==2 for c in clauses)

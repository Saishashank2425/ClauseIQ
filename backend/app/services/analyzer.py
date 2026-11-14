from backend.app.ingestion.extract import extract_document
from backend.app.preprocessing.segment import segment_pages
from backend.app.risk.rules import assess_clause
from backend.app.ml.classifier import predict_clause_category
from backend.app.schemas.analysis import ClauseResult, DocumentAnalysis


def analyze_document(filename: str, content: bytes, enable_ocr: bool = False) -> DocumentAnalysis:
    pages = extract_document(filename, content, enable_ocr=enable_ocr)
    clauses = segment_pages(pages)
    results: list[ClauseResult] = []
    for clause in clauses:
        risk, flags, explanation = assess_clause(clause.text)
        results.append(ClauseResult(
            clause_id=clause.clause_id, text=clause.text, page=clause.page,
            category=predict_clause_category(clause.text) or (flags[0] if flags else "other"), risk_level=risk,
            risk_flags=flags, explanation=explanation,
        ))
    summary = {level: sum(1 for item in results if item.risk_level == level) for level in ("high", "medium", "low")}
    return DocumentAnalysis(
        filename=filename, pages=sum(1 for p in pages if p.page is not None),
        word_count=sum(len(p.text.split()) for p in pages), clauses=results, summary=summary,
    )

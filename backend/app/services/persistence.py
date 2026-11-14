import hashlib, json
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.models import DocumentRecord, ClauseRecord
from backend.app.schemas.analysis import DocumentAnalysis

def persist_analysis(db: Session, filename: str, content: bytes, analysis: DocumentAnalysis) -> int:
    digest = hashlib.sha256(content).hexdigest()
    existing = db.scalar(select(DocumentRecord).where(DocumentRecord.sha256 == digest))
    if existing:
        return existing.id
    record = DocumentRecord(filename=filename[:255], sha256=digest)
    record.clauses = [ClauseRecord(clause_id=c.clause_id, page=c.page, text=c.text,
        category=c.category, risk_level=c.risk_level, risk_flags_json=json.dumps(c.risk_flags)) for c in analysis.clauses]
    db.add(record); db.commit(); db.refresh(record)
    return record.id

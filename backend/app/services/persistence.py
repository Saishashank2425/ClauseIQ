import hashlib
import json
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models import DocumentRecord, ClauseRecord, TenantMembership
from backend.app.schemas.analysis import DocumentAnalysis
from backend.app.retrieval.embeddings import embed_texts


def persist_analysis(
    db: Session,
    filename: str,
    content: bytes,
    analysis: DocumentAnalysis,
    user: dict,
) -> int:
    """Persist a document as a tenant-owned, versioned record.

    Google subject IDs are the only identity values accepted from the verified
    authentication dependency. A user's initial workspace is private to that user.
    """
    subject_id = str(user["id"])
    tenant_id = subject_id
    digest = hashlib.sha256(content).hexdigest()

    existing = db.scalar(
        select(DocumentRecord).where(
            DocumentRecord.tenant_id == tenant_id,
            DocumentRecord.sha256 == digest,
        )
    )
    if existing:
        return existing.id

    latest = db.scalar(
        select(DocumentRecord)
        .where(
            DocumentRecord.tenant_id == tenant_id,
            func.lower(DocumentRecord.filename) == filename.strip().lower(),
        )
        .order_by(DocumentRecord.version_number.desc())
        .limit(1)
        .with_for_update()
    )

    if latest:
        latest.is_current = False
        version_group_id = latest.version_group_id
        version_number = latest.version_number + 1
        supersedes_document_id = latest.id
    else:
        version_group_id = str(uuid.uuid4())
        version_number = 1
        supersedes_document_id = None

    record = DocumentRecord(
        filename=filename[:255],
        sha256=digest,
        tenant_id=tenant_id,
        owner_id=subject_id,
        version_group_id=version_group_id,
        version_number=version_number,
        is_current=True,
        supersedes_document_id=supersedes_document_id,
    )
    vectors = embed_texts([clause.text for clause in analysis.clauses])
    record.clauses = [
        ClauseRecord(
            clause_id=clause.clause_id,
            page=clause.page,
            text=clause.text,
            category=clause.category,
            risk_level=clause.risk_level,
            risk_flags_json=json.dumps(clause.risk_flags),
            embedding=vectors[index] if vectors is not None else None,
        )
        for index, clause in enumerate(analysis.clauses)
    ]

    # Bootstrap only the verified user's private workspace membership.
    membership = db.scalar(
        select(TenantMembership).where(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.subject_id == subject_id,
        )
    )
    if membership is None:
        db.add(TenantMembership(
            tenant_id=tenant_id,
            subject_id=subject_id,
            role="owner",
            active=True,
        ))

    db.add(record)
    db.flush()
    db.commit()
    db.refresh(record)
    return record.id

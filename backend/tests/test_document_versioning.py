"""Versioning regression tests for tenant-scoped persistence."""
import hashlib

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.database.base import Base
from backend.app.models import DocumentRecord, TenantMembership
from backend.app.services.persistence import persist_analysis
from backend.app.schemas.analysis import DocumentAnalysis


def _analysis():
    return DocumentAnalysis(
        filename="msa.pdf",
        pages=1,
        word_count=4,
        clauses=[],
        summary={},
    )


def test_uploading_changed_file_creates_new_current_version():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            user = {"id": "google-sub-alice"}
            first_id = persist_analysis(db, "msa.pdf", b"version one", _analysis(), user)
            second_id = persist_analysis(db, "msa.pdf", b"version two", _analysis(), user)

            rows = db.scalars(
                select(DocumentRecord).where(
                    DocumentRecord.tenant_id == "google-sub-alice"
                ).order_by(DocumentRecord.version_number)
            ).all()

            assert first_id != second_id
            assert [row.version_number for row in rows] == [1, 2]
            assert [row.is_current for row in rows] == [False, True]
            assert rows[1].supersedes_document_id == first_id
            assert rows[0].version_group_id == rows[1].version_group_id
            assert db.scalar(
                select(TenantMembership).where(
                    TenantMembership.subject_id == "google-sub-alice"
                )
            ).role == "owner"
    finally:
        Base.metadata.drop_all(engine)

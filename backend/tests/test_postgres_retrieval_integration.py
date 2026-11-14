"""PostgreSQL integration coverage for pgvector, full text, and SQL ACL filtering."""
import os
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.models import (
    ClauseRecord,
    DocumentPermission,
    DocumentRecord,
    TenantMembership,
)
from backend.app.retrieval.authorized import (
    search_authorized_hybrid,
    search_authorized_vectors,
)


def test_postgres_vector_and_hybrid_search_keep_acl_in_sql(monkeypatch):
    database_url = os.getenv("CLAUSEIQ_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("CLAUSEIQ_TEST_DATABASE_URL is not configured.")

    engine = create_engine(database_url)
    suffix = uuid.uuid4().hex
    tenant_id = "tenant-" + suffix
    private_tenant_id = "private-" + suffix
    subject_id = "reviewer-" + suffix
    query_vector = [1.0] + [0.0] * 383

    try:
        with Session(engine) as db:
            allowed = DocumentRecord(
                filename="allowed.pdf",
                sha256=(suffix + "a").ljust(64, "0")[:64],
                tenant_id=tenant_id,
                owner_id="owner-" + suffix,
                version_group_id="allowed-" + suffix,
                version_number=1,
                is_current=True,
            )
            allowed.clauses = [
                ClauseRecord(
                    clause_id="C0001",
                    page=1,
                    text="Supplier indemnification covers third-party liability claims.",
                    category="indemnification",
                    risk_level="medium",
                    risk_flags_json="[]",
                    embedding=query_vector,
                )
            ]
            private = DocumentRecord(
                filename="private.pdf",
                sha256=(suffix + "b").ljust(64, "0")[:64],
                tenant_id=private_tenant_id,
                owner_id="other-" + suffix,
                version_group_id="private-" + suffix,
                version_number=1,
                is_current=True,
            )
            private.clauses = [
                ClauseRecord(
                    clause_id="C0002",
                    page=1,
                    text="Supplier indemnification covers third-party liability claims.",
                    category="indemnification",
                    risk_level="medium",
                    risk_flags_json="[]",
                    embedding=query_vector,
                )
            ]
            db.add_all([
                allowed,
                private,
                TenantMembership(
                    tenant_id=tenant_id,
                    subject_id=subject_id,
                    role="legal",
                    active=True,
                ),
            ])
            db.flush()
            db.add(DocumentPermission(
                document_id=allowed.id,
                principal_type="user",
                principal_id=subject_id,
                permission="read",
                granted_by=allowed.owner_id,
            ))
            db.commit()

            monkeypatch.setattr(
                "backend.app.retrieval.authorized.embed_texts",
                lambda _texts: [query_vector],
            )
            vector_rows = search_authorized_vectors(
                db, subject_id, query_vector, limit=10
            )
            hybrid_rows = search_authorized_hybrid(
                db,
                subject_id,
                "indemnification liability",
                limit=10,
            )

            assert [row.document_id for row in vector_rows] == [allowed.id]
            assert [row.document_id for row in hybrid_rows] == [allowed.id]
    finally:
        with Session(engine) as db:
            db.query(DocumentRecord).filter(
                DocumentRecord.tenant_id.in_([tenant_id, private_tenant_id])
            ).delete(synchronize_session=False)
            db.query(TenantMembership).filter(
                TenantMembership.tenant_id.in_([tenant_id, private_tenant_id])
            ).delete(synchronize_session=False)
            db.commit()
        engine.dispose()

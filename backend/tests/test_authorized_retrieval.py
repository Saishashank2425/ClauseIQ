"""Security regression tests: unauthorized and superseded clauses never leak."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.database.base import Base
from backend.app.models import (
    ClauseRecord, DocumentPermission, DocumentRecord, TenantMembership,
)
from backend.app.retrieval.authorized import authorized_clauses_query


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


def add_document(db, *, owner, tenant, name, current=True):
    document = DocumentRecord(
        filename=name,
        sha256=(owner + name + str(current)).ljust(64, "0")[:64],
        tenant_id=tenant,
        owner_id=owner,
        version_group_id=owner + "-" + name,
        version_number=1 if current else 2,
        is_current=current,
    )
    document.clauses = [
        ClauseRecord(clause_id="C0001", text=f"confidential clause for {name}")
    ]
    db.add(document)
    db.flush()
    return document


def test_user_sees_only_owned_current_documents(db):
    own = add_document(db, owner="alice", tenant="alice", name="own.pdf")
    add_document(db, owner="bob", tenant="bob", name="private.pdf")
    add_document(db, owner="alice", tenant="alice", name="old.pdf", current=False)
    db.commit()

    rows = authorized_clauses_query(db, "alice").all()
    assert [row.document_id for row in rows] == [own.id]


def test_direct_permission_requires_active_tenant_membership(db):
    shared = add_document(db, owner="bob", tenant="team-1", name="shared.pdf")
    db.add(TenantMembership(tenant_id="team-1", subject_id="alice", role="viewer", active=True))
    db.add(DocumentPermission(
        document_id=shared.id,
        principal_type="user",
        principal_id="alice",
        permission="read",
        granted_by="bob",
    ))
    db.commit()

    assert [row.document_id for row in authorized_clauses_query(db, "alice").all()] == [shared.id]


def test_role_permission_is_applied_in_sql(db):
    shared = add_document(db, owner="bob", tenant="team-1", name="review.pdf")
    db.add(TenantMembership(tenant_id="team-1", subject_id="alice", role="reviewer", active=True))
    db.add(DocumentPermission(
        document_id=shared.id,
        principal_type="role",
        principal_id="reviewer",
        permission="read",
        granted_by="bob",
    ))
    db.commit()

    assert [row.document_id for row in authorized_clauses_query(db, "alice").all()] == [shared.id]


def test_membership_without_document_grant_does_not_expose_document(db):
    add_document(db, owner="bob", tenant="team-1", name="secret.pdf")
    db.add(TenantMembership(tenant_id="team-1", subject_id="alice", role="viewer", active=True))
    db.commit()

    assert authorized_clauses_query(db, "alice").all() == []

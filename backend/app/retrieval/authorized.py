"""SQL-first document authorization and pgvector retrieval.

The permission predicate is part of the SQL statement before rows/chunks are
materialized. Never fetch all chunks and filter them in Python.
"""
from __future__ import annotations

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.orm import Session, Query

from backend.app.models import (
    ClauseRecord,
    DocumentRecord,
    DocumentPermission,
    TenantMembership,
)


READ_PERMISSIONS = ("read", "write", "admin")


def authorized_clauses_query(db: Session, subject_id: str) -> Query:
    """Return a query restricted to current documents the subject may read."""
    member_for_document = exists(
        select(1).where(
            TenantMembership.tenant_id == DocumentRecord.tenant_id,
            TenantMembership.subject_id == subject_id,
            TenantMembership.active.is_(True),
        )
    )
    role_for_document = (
        select(TenantMembership.role)
        .where(
            TenantMembership.tenant_id == DocumentRecord.tenant_id,
            TenantMembership.subject_id == subject_id,
            TenantMembership.active.is_(True),
        )
    )
    direct_grant = exists(
        select(1).where(
            DocumentPermission.document_id == DocumentRecord.id,
            DocumentPermission.principal_type == "user",
            DocumentPermission.principal_id == subject_id,
            DocumentPermission.permission.in_(READ_PERMISSIONS),
        )
    )
    role_grant = exists(
        select(1).where(
            DocumentPermission.document_id == DocumentRecord.id,
            DocumentPermission.principal_type == "role",
            DocumentPermission.principal_id.in_(role_for_document),
            DocumentPermission.permission.in_(READ_PERMISSIONS),
        )
    )
    tenant_admin = exists(
        select(1).where(
            TenantMembership.tenant_id == DocumentRecord.tenant_id,
            TenantMembership.subject_id == subject_id,
            TenantMembership.role.in_(("owner", "admin")),
            TenantMembership.active.is_(True),
        )
    )

    return (
        db.query(ClauseRecord)
        .join(DocumentRecord, ClauseRecord.document_id == DocumentRecord.id)
        .filter(DocumentRecord.is_current.is_(True))
        .filter(
            or_(
                DocumentRecord.owner_id == subject_id,
                and_(member_for_document, or_(tenant_admin, direct_grant, role_grant)),
            )
        )
    )


def authorized_documents_query(db: Session, subject_id: str) -> Query:
    """Return only current documents visible to the verified subject."""
    visible_clause = authorized_clauses_query(db, subject_id).with_entities(
        ClauseRecord.document_id
    ).subquery()
    return (
        db.query(DocumentRecord)
        .filter(DocumentRecord.is_current.is_(True))
        .filter(
            or_(
                DocumentRecord.owner_id == subject_id,
                DocumentRecord.id.in_(select(visible_clause.c.document_id)),
            )
        )
        .distinct()
    )


def search_authorized_vectors(
    db: Session,
    subject_id: str,
    query_embedding: list[float],
    limit: int = 8,
) -> list[ClauseRecord]:
    """Cosine-nearest clauses after SQL-level tenant/ACL/current-version filters."""
    if len(query_embedding) != 384:
        raise ValueError("ClauseIQ embeddings must contain exactly 384 dimensions.")
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100.")
    return (
        authorized_clauses_query(db, subject_id)
        .filter(ClauseRecord.embedding.is_not(None))
        .order_by(ClauseRecord.embedding.cosine_distance(query_embedding))
        .limit(limit)
        .all()
    )

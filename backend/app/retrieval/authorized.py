"""SQL-first authorization and hybrid pgvector retrieval.

The permission predicate is part of every SQL statement before rows/chunks are
materialized. Never fetch all chunks and filter them in Python.
"""
from __future__ import annotations

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session, Query

from backend.app.models import (
    ClauseRecord,
    DocumentRecord,
    DocumentPermission,
    TenantMembership,
)
from backend.app.retrieval.embeddings import embed_texts


READ_PERMISSIONS = ("read", "write", "admin")


def authorized_clauses_query(
    db: Session,
    subject_id: str,
    document_id: int | None = None,
) -> Query:
    """Return a SQL query restricted to current documents the subject may read."""
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

    query = (
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
    if document_id is not None:
        query = query.filter(DocumentRecord.id == document_id)
    return query


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
    document_id: int | None = None,
) -> list[ClauseRecord]:
    """Cosine-nearest clauses after SQL-level tenant/ACL/current-version filters."""
    if len(query_embedding) != 384:
        raise ValueError("ClauseIQ embeddings must contain exactly 384 dimensions.")
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100.")
    return (
        authorized_clauses_query(db, subject_id, document_id)
        .filter(ClauseRecord.embedding.is_not(None))
        .order_by(ClauseRecord.embedding.cosine_distance(query_embedding))
        .limit(limit)
        .all()
    )


def search_authorized_hybrid(
    db: Session,
    subject_id: str,
    query_text: str,
    limit: int = 8,
    document_id: int | None = None,
) -> list[ClauseRecord]:
    """Fuse PostgreSQL full-text and pgvector rankings after applying ACL filters."""
    if not query_text.strip():
        return []
    if limit < 1 or limit > 50:
        raise ValueError("limit must be between 1 and 50.")

    base = authorized_clauses_query(db, subject_id, document_id)
    candidate_limit = min(100, max(limit * 4, 20))
    ranked_ids: dict[int, float] = {}
    rank_constant = 60

    # PostgreSQL full-text channel. The authorization/current-version predicates
    # are already in the base SQL query before the text search and limit.
    text_vector = func.to_tsvector("english", ClauseRecord.text)
    text_query = func.plainto_tsquery("english", query_text)
    lexical_rows = (
        base.filter(text_vector.op("@@")(text_query))
        .order_by(func.ts_rank_cd(text_vector, text_query).desc())
        .limit(candidate_limit)
        .all()
    )
    for rank, clause in enumerate(lexical_rows, start=1):
        ranked_ids[clause.id] = ranked_ids.get(clause.id, 0.0) + 1.0 / (rank_constant + rank)

    # Optional dense channel. If embeddings are disabled, lexical retrieval still works.
    query_vectors = embed_texts([query_text])
    if query_vectors:
        vector_rows = search_authorized_vectors(
            db,
            subject_id,
            query_vectors[0],
            limit=candidate_limit,
            document_id=document_id,
        )
        for rank, clause in enumerate(vector_rows, start=1):
            ranked_ids[clause.id] = ranked_ids.get(clause.id, 0.0) + 1.0 / (rank_constant + rank)

    if not ranked_ids:
        return []

    ordered_ids = [
        clause_id
        for clause_id, _score in sorted(
            ranked_ids.items(), key=lambda item: item[1], reverse=True
        )[:limit]
    ]
    # Reapply the same authorization predicate when hydrating the fused candidates.
    rows = base.filter(ClauseRecord.id.in_(ordered_ids)).all()
    by_id = {row.id: row for row in rows}
    return [by_id[clause_id] for clause_id in ordered_ids if clause_id in by_id]

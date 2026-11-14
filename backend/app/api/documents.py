"""Authenticated APIs for persisted, permission-filtered contract documents."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.api.auth import require_user
from backend.app.database.session import get_db
from backend.app.models import ClauseRecord, DocumentRecord
from backend.app.retrieval.authorized import (
    authorized_documents_query,
    search_authorized_hybrid,
)
from backend.app.rag.answer import answer_question
from backend.app.schemas.analysis import ClauseResult

documents_router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@documents_router.get("")
def list_documents(
    db: Session = Depends(get_db),
    user: dict = Depends(require_user),
):
    """List only current documents visible to the authenticated subject."""
    rows = (
        authorized_documents_query(db, str(user["id"]))
        .order_by(DocumentRecord.created_at.desc())
        .all()
    )
    return {
        "documents": [
            {
                "id": row.id,
                "filename": row.filename,
                "version_number": row.version_number,
                "created_at": row.created_at,
                "source_updated_at": row.source_updated_at,
                "is_current": row.is_current,
            }
            for row in rows
        ]
    }


@documents_router.get("/{document_id}/clauses")
def get_document_clauses(
    document_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_user),
):
    """Fetch clauses only after tenant, role, direct ACL and version filters run in SQL."""
    rows = (
        search_authorized_hybrid(
            db,
            str(user["id"]),
            query_text="contract clauses",
            limit=50,
            document_id=document_id,
        )
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {
        "document_id": document_id,
        "clauses": [
            {
                "clause_id": row.clause_id,
                "page": row.page,
                "text": row.text,
                "category": row.category,
                "risk_level": row.risk_level,
                "risk_flags": json.loads(row.risk_flags_json or "[]"),
            }
            for row in rows
        ],
    }


@documents_router.post("/{document_id}/ask")
def ask_saved_document(
    document_id: int,
    question: str = Query(..., min_length=1, max_length=1500),
    db: Session = Depends(get_db),
    user: dict = Depends(require_user),
):
    """Run hybrid RAG only over clauses the caller is authorized to read."""
    rows = search_authorized_hybrid(
        db,
        str(user["id"]),
        query_text=question,
        limit=8,
        document_id=document_id,
    )
    if not rows:
        # Do not reveal whether an inaccessible document ID exists.
        raise HTTPException(status_code=404, detail="Document not found or no matching evidence.")
    clauses = [
        ClauseResult(
            clause_id=row.clause_id,
            page=row.page,
            text=row.text,
            category=row.category,
            risk_level=row.risk_level,
            risk_flags=json.loads(row.risk_flags_json or "[]"),
            explanation="",
        )
        for row in rows
    ]
    return answer_question(question, clauses)

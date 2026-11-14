from unittest.mock import patch

from backend.app.retrieval.bm25 import BM25Index
from backend.app.rag.answer import answer_question, _evidence_sufficiency, _citations_are_valid
from backend.app.schemas.analysis import ClauseResult


def test_bm25_ranks_relevant_clause():
    docs = ["The supplier must maintain insurance coverage.", "Either party may terminate this agreement with thirty days notice."]
    results = BM25Index(docs).search("termination notice", top_k=1)
    assert results[0][0] == 1


def test_metadata_and_legal_concepts_prevent_false_abstention():
    clause = ClauseResult(
        clause_id="C0001", page=2, category="liability",
        risk_flags=["uncapped_liability", "indemnification"],
        explanation="Broad indemnification language with no stated monetary cap.",
        text="Supplier shall indemnify, defend and hold harmless the Customer from claims, losses and damages.",
    )
    evidence = [{
        "clause_id": clause.clause_id, "page": clause.page, "text": clause.text,
        "category": clause.category, "risk_flags": clause.risk_flags,
        "explanation": clause.explanation,
    }]
    supported, coverage, concepts = _evidence_sufficiency(
        "Explain the indemnification clause and identify risks for the customer.", evidence
    )
    assert supported
    assert coverage > 0
    assert "indemnification" in concepts


def test_unrelated_question_still_abstains():
    clause = ClauseResult(
        clause_id="C0001", page=2, category="liability",
        risk_flags=["indemnification"],
        text="Supplier shall indemnify the customer against third-party claims.",
    )
    result = answer_question("What is the penalty for late payment?", [clause])
    assert result["abstained"]
    assert result["mode"] == "unsupported"


def test_citation_validation_requires_real_source_and_each_answer_line():
    evidence = [{"clause_id": "C0001", "page": 2}]
    assert _citations_are_valid("Supplier indemnifies customer. [C0001, page 2]", evidence)
    assert not _citations_are_valid("Supplier indemnifies customer. [C9999, page 2]", evidence)
    assert not _citations_are_valid("Supplier indemnifies customer. [C0001, page 2]\nIt covers claims.", evidence)


def test_answer_uses_retrieved_evidence_and_citations():
    clause = ClauseResult(
        clause_id="C0001", page=2, category="liability",
        risk_flags=["indemnification"],
        text="Supplier shall indemnify the Customer against claims, losses and reasonable legal fees.",
    )
    fake = {
        "text": "The supplier must indemnify the customer against claims and losses. [C0001, page 2]",
        "status": "ok", "provider": "test", "model": "test-model", "usage": {},
    }
    with patch("backend.app.rag.answer.generate", return_value=fake):
        result = answer_question("Explain supplier indemnification obligations.", [clause])
    assert not result["abstained"]
    assert result["mode"] == "grounded_llm"
    assert result["evidence"][0]["clause_id"] == "C0001"


def test_answer_returns_evidence_but_abstains_without_llm():
    clauses = [ClauseResult(clause_id="C0001", text="Supplier shall maintain insurance coverage.", page=2)]
    with patch("backend.app.rag.answer.generate", return_value={"text": None, "status": "no_free_provider_configured"}):
        result = answer_question("What insurance coverage must supplier maintain?", clauses)
    assert result["abstained"]
    assert result["evidence"][0]["page"] == 2
    assert result["mode"] == "no_free_provider_configured"

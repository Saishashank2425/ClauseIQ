from backend.app.retrieval.bm25 import BM25Index
from backend.app.rag.answer import answer_question
from backend.app.schemas.analysis import ClauseResult

def test_bm25_ranks_relevant_clause():
    docs = ["The supplier must maintain insurance coverage.", "Either party may terminate this agreement with thirty days notice."]
    results = BM25Index(docs).search("termination notice", top_k=1)
    assert results[0][0] == 1

def test_answer_returns_evidence_and_abstains_on_no_match():
    clauses = [ClauseResult(clause_id="C1", text="Supplier shall maintain insurance coverage.", page=2)]
    result = answer_question("insurance coverage", clauses)
    assert not result["abstained"] and result["evidence"][0]["page"] == 2
    empty = answer_question("quantum computing", clauses)
    assert empty["abstained"]

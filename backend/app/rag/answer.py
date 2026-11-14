"""Evidence-first extractive answering with explicit abstention."""
from __future__ import annotations
from backend.app.retrieval.hybrid import HybridRetriever
from backend.app.schemas.analysis import ClauseResult

def answer_question(question: str, clauses: list[ClauseResult], top_k: int = 4) -> dict:
    if not question.strip():
        return {"answer": "Please provide a question.", "abstained": True, "evidence": []}
    if not clauses:
        return {"answer": "I could not find supporting text in the supplied document.", "abstained": True, "evidence": []}
    retriever = HybridRetriever([c.text for c in clauses])
    ranked = retriever.search(question, top_k=top_k)
    if not ranked or ranked[0][1] < 0.08:
        return {"answer": "I could not find a sufficiently relevant clause in the supplied document. Try rephrasing or consult the full contract.", "abstained": True, "evidence": []}
    evidence = []
    for idx, score in ranked:
        clause = clauses[idx]
        evidence.append({"clause_id": clause.clause_id, "page": clause.page, "text": clause.text[:1800], "relevance_score": round(score, 4)})
    answer = "The most relevant contract language is shown in the cited evidence. Review the quoted clause in context; this prototype does not infer legal meaning beyond the source text."
    return {"answer": answer, "abstained": False, "evidence": evidence}

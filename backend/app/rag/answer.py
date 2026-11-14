"""Evidence-first contract Q&A with provider failover and strict citation checks."""
from __future__ import annotations
import logging, re
from backend.app.observability import trace_observation
from backend.app.rag.providers import generate
from backend.app.retrieval.hybrid import HybridRetriever
from backend.app.schemas.analysis import ClauseResult

logger = logging.getLogger(__name__)
CITATION_RE = re.compile(r"\[(C\d{4})(?:, page (\d+))?\]")
WORD_RE = re.compile(r"[a-z0-9]+")
STOP_WORDS = {"a","an","and","are","as","at","be","by","can","does","for","from","how","in","is","it","of","on","or","the","this","to","under","was","what","when","where","which","who","why","will","with","would","agreement","contract","clause","clauses","party","parties","document","tell","me","about"}

def _query_coverage(question: str, evidence: list[dict]) -> float:
    terms = {t for t in WORD_RE.findall(question.lower()) if len(t) > 2 and t not in STOP_WORDS}
    if not terms:
        return 0.0
    corpus = " ".join(item.get("text", "") for item in evidence).lower()
    return len({t for t in terms if re.search(r"\b" + re.escape(t) + r"\b", corpus)}) / len(terms)

def _citations_are_valid(answer: str, evidence: list[dict]) -> bool:
    citations = CITATION_RE.findall(answer)
    if not citations:
        return False
    known = {item["clause_id"] for item in evidence}
    for clause_id, page in citations:
        if clause_id not in known:
            return False
        if page and page not in {str(item["page"]) for item in evidence if item["clause_id"] == clause_id and item.get("page") is not None}:
            return False
    for paragraph in [p.strip() for p in answer.splitlines() if p.strip()]:
        if not CITATION_RE.search(paragraph) and not paragraph.startswith(("-", "•", "#")):
            return False
    return True

def answer_question(question: str, clauses: list[ClauseResult], top_k: int = 4) -> dict:
    if not question.strip():
        return {"answer": "Please provide a question.", "abstained": True, "evidence": [], "mode": "abstain"}
    if not clauses:
        return {"answer": "The selected document contains no extractable clauses.", "abstained": True, "evidence": [], "mode": "abstain"}

    with trace_observation("clauseiq.rag.request", {"pipeline": "bm25_tfidf_optional_dense_rerank", "clause_count": len(clauses)}):
        retriever = HybridRetriever([clause.text for clause in clauses])
        ranked = retriever.search(question, top_k=top_k)
        if not ranked:
            return {"answer": "I cannot find supporting evidence in the selected document, so I will not guess.", "abstained": True, "evidence": [], "mode": "unsupported"}
        evidence = []
        for idx, score in ranked:
            clause = clauses[idx]
            evidence.append({"clause_id": clause.clause_id, "page": clause.page, "text": clause.text[:1800], "relevance_score": round(score, 4)})
        coverage = _query_coverage(question, evidence)
        if coverage < 0.18:
            return {"answer": "The retrieved passages do not contain enough direct support for this question. I cannot answer without guessing.", "abstained": True, "evidence": evidence, "mode": "unsupported"}

        messages = [
            {"role": "system", "content": (
                "You are ClauseIQ, an evidence-only contract text assistant. Use ONLY the supplied excerpts. "
                "Do not use outside knowledge, legal assumptions, or inferred facts. If excerpts do not directly "
                "answer, say the document does not establish the answer. Every factual sentence and bullet must end "
                "with exact citations such as [C0001, page 2]. Use only supplied clause IDs and page numbers. "
                "Never invent citations. If evidence conflicts or is incomplete, explain the limitation and abstain. "
                "Do not give legal advice."
            )},
            {"role": "user", "content": "Question: " + question + "\n\nEvidence excerpts:\n" + "\n\n".join(
                f"[{item['clause_id']}, page {item['page']}]\n{item['text']}" if item.get("page") else f"[{item['clause_id']}]\n{item['text']}" for item in evidence
            )},
        ]
        result = generate(messages)
        generated = result.get("text")
        if not generated or not _citations_are_valid(generated, evidence):
            status = result.get("status", "invalid_citations") if not generated else "invalid_citations"
            message = "No free LLM provider is configured. Retrieved evidence is shown below; no answer was generated." if status == "no_free_provider_configured" else "The answer could not be generated or did not pass citation validation. Retrieved evidence is shown below; no answer was generated."
            return {"answer": message, "abstained": True, "evidence": evidence, "mode": status, "provider": result.get("provider"), "model": result.get("model")}
        return {"answer": generated, "abstained": False, "evidence": evidence, "mode": "grounded_llm", "provider": result.get("provider"), "model": result.get("model"), "usage": result.get("usage", {})}

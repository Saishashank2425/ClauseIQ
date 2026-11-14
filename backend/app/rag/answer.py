"""Grounded contract Q&A: retrieve evidence first, then optionally generate from it."""
from __future__ import annotations
import os
import re
import httpx
from backend.app.retrieval.hybrid import HybridRetriever
from backend.app.schemas.analysis import ClauseResult

def _generate_with_llm(question: str, evidence: list[dict]) -> str | None:
    base = os.getenv("CLAUSEIQ_LLM_BASE_URL", "").rstrip("/")
    model = os.getenv("CLAUSEIQ_LLM_MODEL", "")
    if not base or not model:
        return None
    api_key = os.getenv("CLAUSEIQ_LLM_API_KEY", "")
    passages = "\n\n".join(
        f"[{item['clause_id']}" + (f", page {item['page']}" if item.get("page") else "") + f"]\n{item['text']}"
        for item in evidence
    )
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": "You are a contract text assistant. Answer only from the supplied excerpts. Do not use outside knowledge or infer missing terms. If the excerpts do not answer the question, say exactly that the supplied excerpts do not establish the answer. Cite every factual statement using the exact clause citation format [C0001] or [C0001, page 2]. Never invent clause IDs or page numbers. Do not provide legal advice."},
            {"role": "user", "content": f"Question: {question}\n\nEvidence excerpts:\n{passages}"}
        ]
    }
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        response = httpx.post(f"{base}/chat/completions", json=payload, headers=headers, timeout=35.0)
        response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"].strip()
        known = {item["clause_id"] for item in evidence}
        citations = re.findall(r"\[(C\d{4})(?:, page \d+)?\]", text)
        if not citations or any(citation not in known for citation in citations):
            return None
        return text
    except Exception:
        return None

def answer_question(question: str, clauses: list[ClauseResult], top_k: int = 4) -> dict:
    if not question.strip():
        return {"answer": "Please provide a question.", "abstained": True, "evidence": [], "mode": "abstain"}
    if not clauses:
        return {"answer": "I could not find supporting text in the supplied document.", "abstained": True, "evidence": [], "mode": "abstain"}
    retriever = HybridRetriever([clause.text for clause in clauses])
    ranked = retriever.search(question, top_k=top_k)
    if not ranked or ranked[0][1] < 0.12:
        return {"answer": "The supplied document does not contain sufficiently relevant evidence to answer this question.", "abstained": True, "evidence": [], "mode": "abstain"}
    evidence = []
    for idx, score in ranked:
        clause = clauses[idx]
        evidence.append({"clause_id": clause.clause_id, "page": clause.page,
                         "text": clause.text[:1800], "relevance_score": round(score, 4)})
    generated = _generate_with_llm(question, evidence)
    if generated:
        return {"answer": generated, "abstained": False, "evidence": evidence, "mode": "grounded_llm"}
    answer = "I found potentially relevant contract language. The excerpts below are the evidence to review; this deployment has no configured LLM answer generator, so it does not infer the legal effect."
    return {"answer": answer, "abstained": False, "evidence": evidence, "mode": "extractive"}

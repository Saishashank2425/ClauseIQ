"""Evidence-first contract Q&A with relevance-aware abstention and citation checks."""
from __future__ import annotations

import logging
import re
import time
from typing import Any

from backend.app.observability import trace_observation
from backend.app.rag.providers import generate
from backend.app.retrieval.hybrid import HybridRetriever
from backend.app.schemas.analysis import ClauseResult

logger = logging.getLogger(__name__)
CITATION_RE = re.compile(r"\[(C\d{4})(?:, page (\d+))?\]")
WORD_RE = re.compile(r"[a-z0-9]+")
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "by", "can",
    "could", "does", "do", "for", "from", "give", "has", "have", "how", "i",
    "in", "is", "it", "its", "me", "of", "on", "or", "please", "should", "tell",
    "that", "the", "their", "this", "to", "was", "what", "when", "where", "which",
    "who", "why", "will", "with", "would", "explain", "describe", "identify",
    "summarize", "summary", "agreement", "contract", "clause", "clauses", "party",
    "parties", "document", "customer", "supplier",
}
CONCEPTS = {
    "indemnification": {"indemnification", "indemnify", "indemnifies", "indemnified", "hold harmless", "defend"},
    "liability": {"liability", "liable", "losses", "damages", "claims", "expenses", "costs"},
    "termination": {"termination", "terminate", "terminated", "notice", "cure", "breach"},
    "renewal": {"renewal", "renew", "automatically", "non-renewal", "expiry", "term"},
    "confidentiality": {"confidentiality", "confidential", "trade secret", "disclose", "disclosure"},
    "governing_law": {"governing law", "jurisdiction", "venue", "courts", "law"},
    "payment": {"payment", "invoice", "late fee", "penalty", "interest", "overdue"},
}


def _tokens(value: str) -> set[str]:
    return {token for token in WORD_RE.findall(value.lower()) if len(token) > 2}


def _evidence_sufficiency(question: str, evidence: list[dict[str, Any]]) -> tuple[bool, float, list[str]]:
    """A lightweight guard against clearly unrelated retrieval, not a semantic gate.

    Query words such as 'risks' or 'explain' need not literally occur in a clause.
    Clause metadata and legal concept aliases are included to reduce false abstentions.
    """
    if not evidence:
        return False, 0.0, []
    question_tokens = _tokens(question) - STOP_WORDS
    evidence_text = " ".join(
        " ".join(str(item.get(key, "")) for key in ("text", "category", "risk_flags", "explanation"))
        for item in evidence
    ).lower()
    evidence_tokens = _tokens(evidence_text)
    matched = sorted(question_tokens & evidence_tokens)
    expanded_matches: list[str] = []
    for concept, aliases in CONCEPTS.items():
        q_has_concept = concept.replace("_", " ") in question.lower() or any(
            alias in question.lower() for alias in aliases
        )
        e_has_concept = any(alias in evidence_text for alias in aliases)
        if q_has_concept and e_has_concept:
            expanded_matches.append(concept)
    denominator = max(len(question_tokens), 1)
    coverage = min(1.0, (len(matched) + 1.5 * len(expanded_matches)) / denominator)
    # A single specific concept match is enough for short questions; unrelated questions
    # with no lexical or domain-concept overlap still abstain.
    supported = bool(matched or expanded_matches)
    return supported, round(coverage, 3), sorted(set(matched + expanded_matches))


def _citations_are_valid(answer: str, evidence: list[dict[str, Any]]) -> bool:
    citations = CITATION_RE.findall(answer)
    if not citations:
        return False
    known_pages = {
        (str(item["clause_id"]), str(item["page"]))
        for item in evidence
        if item.get("page") is not None
    }
    known_ids = {str(item["clause_id"]) for item in evidence}
    for clause_id, page in citations:
        if clause_id not in known_ids:
            return False
        if page and (clause_id, page) not in known_pages:
            return False

    # Every prose/bullet line must carry a citation. Headings are allowed but are
    # not considered factual answer content.
    for line in (part.strip() for part in answer.splitlines() if part.strip()):
        if line.startswith("#"):
            continue
        if not CITATION_RE.search(line):
            return False
    return True


def answer_question(question: str, clauses: list[ClauseResult], top_k: int = 4) -> dict:
    started = time.perf_counter()
    if not question.strip():
        return {"answer": "Please provide a question.", "abstained": True, "evidence": [], "mode": "abstain"}
    if not clauses:
        return {"answer": "The selected document contains no extractable clauses.", "abstained": True, "evidence": [], "mode": "abstain"}

    # Index clause text plus structured clause metadata. This helps retrieve evidence
    # for questions about risk/impact even when those exact words are absent in the text.
    retrieval_docs = [
        " ".join([c.text, c.category, " ".join(c.risk_flags), c.explanation])
        for c in clauses
    ]
    with trace_observation("clauseiq.rag.request", {"pipeline": "bm25_tfidf_rrf_optional_dense_cross_encoder", "clause_count": len(clauses)}):
        retriever = HybridRetriever(retrieval_docs)
        ranked = retriever.search(question, top_k=top_k)
        if not ranked:
            return {
                "answer": "I cannot find supporting evidence in the selected document, so I will not guess.",
                "abstained": True, "evidence": [], "mode": "unsupported",
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            }

        evidence = []
        for idx, score in ranked:
            clause = clauses[idx]
            evidence.append({
                "clause_id": clause.clause_id,
                "page": clause.page,
                "text": clause.text[:2400],
                "category": clause.category,
                "risk_flags": clause.risk_flags,
                "explanation": clause.explanation,
                "relevance_score": round(score, 4),
            })

        supported, coverage, matched_concepts = _evidence_sufficiency(question, evidence)
        if not supported:
            return {
                "answer": "The retrieved passages do not directly support this question. I cannot answer without guessing.",
                "abstained": True, "evidence": evidence, "mode": "unsupported",
                "retrieval_coverage": coverage,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            }

        messages = [
            {"role": "system", "content": (
                "You are ClauseIQ, an evidence-only contract text assistant. Answer the user's question "
                "using ONLY the supplied excerpts. Do not use outside knowledge, legal assumptions, or "
                "inferred facts. Explain the clause's practical textual implications only when directly "
                "supported by its wording. Every factual sentence and every bullet must end with exact "
                "citations such as [C0001, page 2]. Use only supplied clause IDs and page numbers. "
                "Never invent citations. If evidence is incomplete, say exactly what the document does "
                "and does not establish. Do not give legal advice."
            )},
            {"role": "user", "content": "Question: " + question + "\n\nEvidence excerpts:\n" + "\n\n".join(
                f"[{item['clause_id']}, page {item['page']}]\n{item['text']}\nClause category: {item['category']}\nRisk indicators: {', '.join(item['risk_flags'])}\nAnalysis note: {item['explanation']}"
                if item.get("page") is not None else f"[{item['clause_id']}]\n{item['text']}"
                for item in evidence
            )},
        ]
        result = generate(messages)
        generated = result.get("text")
        if not generated or not _citations_are_valid(generated, evidence):
            status = result.get("status", "invalid_citations") if not generated else "invalid_citations"
            message = (
                "No free LLM provider is configured. Retrieved evidence is shown below; no answer was generated."
                if status == "no_free_provider_configured"
                else "The answer could not be generated or did not pass citation validation. Retrieved evidence is shown below; no answer was generated."
            )
            return {
                "answer": message, "abstained": True, "evidence": evidence, "mode": status,
                "provider": result.get("provider"), "model": result.get("model"),
                "retrieval_coverage": coverage,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            }
        return {
            "answer": generated, "abstained": False, "evidence": evidence, "mode": "grounded_llm",
            "provider": result.get("provider"), "model": result.get("model"),
            "usage": result.get("usage", {}), "retrieval_coverage": coverage,
            "matched_concepts": matched_concepts,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }

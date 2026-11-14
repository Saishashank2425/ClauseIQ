"""Grounded contract Q&A with safe LLM diagnostics and extractive fallback."""
from __future__ import annotations

import logging
import os
import re
import time
from typing import Any

import httpx

from backend.app.retrieval.hybrid import HybridRetriever
from backend.app.schemas.analysis import ClauseResult

logger = logging.getLogger(__name__)
CITATION_RE = re.compile(r"\\[(C\\d{4})(?:, page (\\d+))?\\]")


def _message_text(content: Any) -> str:
    """Normalize OpenAI-compatible text content without assuming a string response."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "\\n".join(parts).strip()
    return ""


def _generate_with_llm(question: str, evidence: list[dict]) -> tuple[str | None, str]:
    base = os.getenv("CLAUSEIQ_LLM_BASE_URL", "").strip().rstrip("/")
    model = os.getenv("CLAUSEIQ_LLM_MODEL", "").strip()
    api_key = os.getenv("CLAUSEIQ_LLM_API_KEY", "").strip()

    if not base or not model:
        logger.warning("ClauseIQ LLM is not configured: base_url_set=%s model_set=%s", bool(base), bool(model))
        return None, "llm_not_configured"
    if not api_key:
        logger.error("ClauseIQ LLM configuration is incomplete: API key is missing")
        return None, "llm_missing_api_key"

    passages = "\\n\\n".join(
        f"[{item['clause_id']}" + (f", page {item['page']}" if item.get("page") else "") + f"]\\n{item['text']}"
        for item in evidence
    )
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a contract text assistant. Answer only from the supplied excerpts. "
                    "Do not use outside knowledge or infer missing terms. If the excerpts do not "
                    "answer the question, say that the supplied excerpts do not establish the answer. "
                    "Cite every factual statement using exact clause citations [C0001] or "
                    "[C0001, page 2]. Never invent clause IDs or page numbers. Do not provide legal advice."
                ),
            },
            {"role": "user", "content": f"Question: {question}\\n\\nEvidence excerpts:\\n{passages}"},
        ],
    }

    try:
        response = None
        # Gemini can temporarily return 429/5xx while capacity is constrained.
        # Retry a small, bounded number of times; never retry auth or bad-request errors.
        for attempt in range(3):
            response = httpx.post(
                f"{base}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
            if response.status_code not in (429, 500, 502, 503, 504) or attempt == 2:
                break
            retry_after = response.headers.get("Retry-After", "")
            try:
                delay = min(max(float(retry_after), 0.5), 3.0) if retry_after else (1.0, 2.0)[attempt]
            except ValueError:
                delay = (1.0, 2.0)[attempt]
            logger.warning(
                "ClauseIQ LLM provider returned transient HTTP %s; retrying attempt %s/3 after %.1fs (model=%s)",
                response.status_code, attempt + 2, delay, model,
            )
            time.sleep(delay)

        if response is not None and response.is_error:
            # Never log request headers, API keys, prompts, or contract text.
            logger.error("ClauseIQ LLM provider returned HTTP %s after retries (model=%s)", response.status_code, model)
            if response.status_code == 503:
                return None, "llm_provider_overloaded"
            if response.status_code == 429:
                return None, "llm_rate_limited"
            return None, "llm_provider_error"

        data = response.json()
        choices = data.get("choices") if isinstance(data, dict) else None
        message = choices[0].get("message", {}) if isinstance(choices, list) and choices else {}
        generated = _message_text(message.get("content") if isinstance(message, dict) else None)
        if not generated:
            logger.error("ClauseIQ LLM provider returned no text content (model=%s)", model)
            return None, "llm_empty_response"

        known = {item["clause_id"] for item in evidence}
        citations = CITATION_RE.findall(generated)
        if not citations:
            logger.warning("ClauseIQ LLM response rejected: no clause citations (model=%s)", model)
            return None, "llm_invalid_citations"
        for clause_id, page in citations:
            if clause_id not in known:
                logger.warning("ClauseIQ LLM response rejected: unknown clause citation (model=%s)", model)
                return None, "llm_invalid_citations"
            if page:
                known_pages = {str(item["page"]) for item in evidence if item["clause_id"] == clause_id and item.get("page") is not None}
                if page not in known_pages:
                    logger.warning("ClauseIQ LLM response rejected: invalid page citation (model=%s)", model)
                    return None, "llm_invalid_citations"
        return generated, "grounded_llm"

    except httpx.TimeoutException:
        logger.error("ClauseIQ LLM request timed out (model=%s)", model)
        return None, "llm_timeout"
    except httpx.RequestError as exc:
        logger.error("ClauseIQ LLM network request failed (%s, model=%s)", type(exc).__name__, model)
        return None, "llm_network_error"
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        logger.exception("ClauseIQ LLM response could not be parsed (%s, model=%s)", type(exc).__name__, model)
        return None, "llm_invalid_response"
    except Exception as exc:
        logger.exception("Unexpected ClauseIQ LLM failure (%s, model=%s)", type(exc).__name__, model)
        return None, "llm_error"


def answer_question(question: str, clauses: list[ClauseResult], top_k: int = 4) -> dict:
    if not question.strip():
        return {"answer": "Please provide a question.", "abstained": True, "evidence": [], "mode": "abstain"}
    if not clauses:
        return {"answer": "I could not find supporting text in the supplied document.", "abstained": True, "evidence": [], "mode": "abstain"}

    retriever = HybridRetriever([clause.text for clause in clauses])
    ranked = retriever.search(question, top_k=top_k)
    if not ranked or ranked[0][1] < 0.12:
        return {
            "answer": "The supplied document does not contain sufficiently relevant evidence to answer this question.",
            "abstained": True,
            "evidence": [],
            "mode": "abstain",
        }

    evidence = []
    for idx, score in ranked:
        clause = clauses[idx]
        evidence.append({
            "clause_id": clause.clause_id,
            "page": clause.page,
            "text": clause.text[:1800],
            "relevance_score": round(score, 4),
        })

    generated, llm_status = _generate_with_llm(question, evidence)
    if generated:
        return {"answer": generated, "abstained": False, "evidence": evidence, "mode": "grounded_llm"}

    fallback_messages = {
        "llm_not_configured": "AI answer generation is not configured. Retrieved contract evidence is shown below.",
        "llm_missing_api_key": "AI answer generation is missing its provider API key. Retrieved evidence is shown below.",
        "llm_timeout": "The AI provider timed out. Retrieved evidence is shown below; please retry.",
        "llm_provider_error": "The AI provider could not process the request. Retrieved evidence is shown below; please retry.",
        "llm_provider_overloaded": "Gemini is temporarily overloaded. ClauseIQ retried automatically, but the provider is still busy. Your retrieved evidence is shown below; please try again shortly.",
        "llm_rate_limited": "Gemini rate-limited this request. Your retrieved evidence is shown below; please try again shortly.",
        "llm_invalid_citations": "The AI response did not pass citation validation. Retrieved evidence is shown below instead.",
    }
    answer = fallback_messages.get(
        llm_status,
        "AI answer generation is temporarily unavailable. Retrieved evidence is shown below; please retry.",
    )
    return {
        "answer": answer,
        "abstained": False,
        "evidence": evidence,
        "mode": llm_status,
    }

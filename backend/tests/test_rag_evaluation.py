import json
from pathlib import Path

from scripts.evaluate_rag import score_case, summarize_results
from backend.app.api.demo import DEMO_CLAUSES
from backend.app.rag.answer import answer_question


ROOT = Path(__file__).resolve().parents[2]


def test_golden_evaluation_dataset_has_50_unique_cases():
    dataset = ROOT / "datasets" / "evaluation" / "clauseiq_golden_50.jsonl"
    rows = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]

    assert len(rows) == 50
    assert len({row["id"] for row in rows}) == 50
    assert all(row["question"] and row["reference_answer"] for row in rows)
    assert all(row["expected_clause_id"] and row["expected_page"] for row in rows)


def test_score_case_requires_retrieved_and_cited_expected_source():
    case = {"expected_clause_id": "C0001", "expected_page": 2}
    result = {
        "answer": "Supplier must defend the customer [C0001, page 2].",
        "evidence": [{"clause_id": "C0001", "page": 2}],
        "abstained": False,
    }

    assert score_case(case, result) == {
        "citation_valid": True,
        "expected_source_retrieved": True,
        "expected_source_cited": True,
        "abstained": False,
        "passed": True,
    }


def test_score_case_rejects_unverified_citation_and_abstention():
    case = {"expected_clause_id": "C0001", "expected_page": 2}
    result = {
        "answer": "It is allowed [C9999, page 9].",
        "evidence": [{"clause_id": "C0001", "page": 2}],
        "abstained": True,
    }

    score = score_case(case, result)
    assert score["citation_valid"] is False
    assert score["expected_source_retrieved"] is True
    assert score["expected_source_cited"] is False
    assert score["passed"] is False


def test_summary_reports_retrieval_citation_abstention_and_latency():
    summary = summarize_results([
        {
            "citation_valid": True,
            "expected_source_retrieved": True,
            "expected_source_cited": True,
            "passed": True,
            "abstained": False,
            "mode": "grounded_llm",
            "latency_ms": 100,
            "provider": "provider-a",
            "model": "model-a",
        },
        {
            "citation_valid": False,
            "expected_source_retrieved": False,
            "expected_source_cited": False,
            "passed": False,
            "abstained": True,
            "mode": "unsupported",
            "latency_ms": 300,
        },
    ])

    assert summary["case_count"] == 2
    assert summary["pass_rate"] == 0.5
    assert summary["citation_syntax_accuracy"] == 0.5
    assert summary["expected_source_retrieval_recall"] == 0.5
    assert summary["expected_source_citation_accuracy"] == 0.5
    assert summary["abstention_rate"] == 0.5
    assert summary["unsupported_rate"] == 0.5
    assert summary["latency_ms"] == {"p50": 200.0, "p95": 290.0}
    assert summary["providers"] == ["provider-a"]

def test_golden_50_pipeline_retrieval_and_citation_gates(monkeypatch):
    import re

    dataset = ROOT / "datasets" / "evaluation" / "clauseiq_golden_50.jsonl"
    cases = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]

    def deterministic_cited_response(messages):
        cited_sources = re.findall(r"\\[(C\\d{4}), page (\\d+)\\]", messages[-1]["content"])
        citations = " ".join(f"[{clause_id}, page {page}]" for clause_id, page in cited_sources)
        return {
            "text": "Sources: " + citations,
            "provider": "test-fixture",
            "model": "deterministic-citation-fixture",
            "usage": {},
        }

    monkeypatch.setattr("backend.app.rag.answer.generate", deterministic_cited_response)
    rows = []
    for case in cases:
        result = answer_question(case["question"], DEMO_CLAUSES, top_k=3)
        rows.append({
            **score_case(case, result),
            "mode": result.get("mode"),
            "latency_ms": result.get("latency_ms"),
            "provider": result.get("provider"),
            "model": result.get("model"),
        })

    summary = summarize_results(rows)
    assert summary["case_count"] == 50
    assert summary["expected_source_retrieval_recall"] == 1.0
    assert summary["expected_source_citation_accuracy"] == 1.0
    assert summary["citation_syntax_accuracy"] == 1.0
    assert summary["abstention_rate"] == 0.0

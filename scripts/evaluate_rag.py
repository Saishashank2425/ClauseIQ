"""Run the 50-question ClauseIQ golden set and optional RAGAS scoring.

Set CLAUSEIQ_BASE_URL to a running ClauseIQ deployment. For LLM-as-judge metrics,
set RAGAS_API_KEY and RAGAS_BASE_URL (Groq-compatible endpoint is supported).
"""
from __future__ import annotations
import json, os, re, time
from datetime import datetime, timezone
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "datasets" / "evaluation" / "clauseiq_golden_50.jsonl"

CITATION = re.compile(r"\[(C\d{4})(?:, page (\d+))?\]")


def score_case(case: dict, result: dict) -> dict:
    """Score retrieval/citation gates without judging free-form answer semantics."""
    evidence = result.get("evidence", [])
    citations = CITATION.findall(result.get("answer", ""))
    valid_ids = {str(item.get("clause_id")) for item in evidence}
    valid_pages = {
        (str(item.get("clause_id")), str(item.get("page")))
        for item in evidence if item.get("page") is not None
    }
    citation_valid = bool(citations) and all(
        clause_id in valid_ids and (not page or (clause_id, page) in valid_pages)
        for clause_id, page in citations
    )
    expected_id = str(case["expected_clause_id"])
    expected_page = str(case["expected_page"])
    expected_source_retrieved = any(
        str(item.get("clause_id")) == expected_id
        and str(item.get("page")) == expected_page for item in evidence
    )
    expected_source_cited = (expected_id, expected_page) in citations
    abstained = bool(result.get("abstained", False))
    return {
        "citation_valid": citation_valid,
        "expected_source_retrieved": expected_source_retrieved,
        "expected_source_cited": expected_source_cited,
        "abstained": abstained,
        "passed": citation_valid and expected_source_retrieved and expected_source_cited and not abstained,
    }


def summarize_results(rows: list[dict]) -> dict:
    """Summarize deterministic gates and operational signals from one evaluation run."""
    count = len(rows)
    latencies = sorted(
        float(row["latency_ms"]) for row in rows if row.get("latency_ms") is not None
    )

    def percentile(fraction: float):
        if not latencies:
            return None
        index = max(0, min(len(latencies) - 1, int((len(latencies) - 1) * fraction + 0.5)))
        return round(latencies[index], 2)

    def rate(field: str):
        return round(sum(bool(row.get(field)) for row in rows) / count, 4) if count else 0.0

    return {
        "case_count": count,
        "citation_syntax_accuracy": rate("citation_valid"),
        "expected_source_retrieval_recall": rate("expected_source_retrieved"),
        "expected_source_citation_accuracy": rate("expected_source_cited"),
        "pass_rate": rate("passed"),
        "abstention_rate": rate("abstained"),
        "unsupported_rate": round(sum(row.get("mode") == "unsupported" for row in rows) / count, 4) if count else 0.0,
        "latency_ms": {"p50": percentile(0.50), "p95": percentile(0.95)},
        "providers": sorted({str(row["provider"]) for row in rows if row.get("provider")}),
        "models": sorted({str(row["model"]) for row in rows if row.get("model")}),
    }

def main() -> None:
    base = os.getenv("CLAUSEIQ_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    cases = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows, citation_ok = [], 0
    with httpx.Client(timeout=90.0) as client:
        for i, case in enumerate(cases, 1):
            request_started = time.perf_counter()
            response = client.post(base + "/api/v1/demo/ask", json={"question": case["question"]})
            request_latency_ms = round((time.perf_counter() - request_started) * 1000, 2)
            response.raise_for_status()
            result = response.json()
            score = score_case(case, result)
            citation_ok += int(score["passed"])
            evidence = result.get("evidence", [])
            latency_ms = result.get("latency_ms")
            if not isinstance(latency_ms, (int, float)):
                latency_ms = request_latency_ms
            rows.append({
                "user_input": case["question"],
                "response": result.get("answer", ""),
                "retrieved_contexts": [item.get("text", "") for item in evidence],
                "reference": case["reference_answer"],
                **score,
                "mode": result.get("mode"),
                "provider": result.get("provider"),
                "model": result.get("model"),
                "latency_ms": round(float(latency_ms), 2),
                "usage": result.get("usage") or {},
            })
            print(f"[{i:02d}/{len(cases)}] {'PASS' if passed else 'CHECK'} {case['id']} mode={result.get('mode')}")
            time.sleep(0.15)

    import csv
    out_csv = ROOT / "ragas_golden_results.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "retrieved_contexts": json.dumps(row["retrieved_contexts"], ensure_ascii=False)})

    summary = summarize_results(rows)
    summary["generated_at"] = datetime.now(timezone.utc).isoformat()
    summary_path = ROOT / "ragas_golden_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"\nPass gate: {citation_ok}/{len(rows)} ({citation_ok / max(len(rows), 1):.1%})")
    print(f"Citation syntax accuracy: {summary['citation_syntax_accuracy']:.1%}")
    print(f"Expected-source retrieval recall: {summary['expected_source_retrieval_recall']:.1%}")
    print(f"Expected-source citation accuracy: {summary['expected_source_citation_accuracy']:.1%}")
    print(f"Latency p50/p95: {summary['latency_ms']['p50']} / {summary['latency_ms']['p95']} ms")
    print(f"Detailed results: {out_csv}")
    print(f"Run summary: {summary_path}")
    key = os.getenv("RAGAS_API_KEY", "")
    if not key:
        print("RAGAS LLM scoring skipped: set RAGAS_API_KEY and RAGAS_BASE_URL to enable free-tier LLM-as-judge metrics.")
        return

    from datasets import Dataset
    from langchain_openai import ChatOpenAI
    from ragas import evaluate
    from ragas.metrics import answer_correctness, context_precision, context_recall, faithfulness

    eval_llm = ChatOpenAI(
        model=os.getenv("RAGAS_MODEL", "openai/gpt-oss-120b"),
        api_key=key,
        base_url=os.getenv("RAGAS_BASE_URL", "https://api.groq.com/openai/v1"),
        temperature=0,
        timeout=60,
        max_retries=1,
    )
    eval_rows = [{k: row[k] for k in ("user_input", "response", "retrieved_contexts", "reference")} for row in rows]
    dataset = Dataset.from_list(eval_rows)
    scores = evaluate(
        dataset,
        metrics=[faithfulness, context_precision, context_recall, answer_correctness],
        llm=eval_llm,
    )
    print("\nRAGAS scores:")
    print(scores)
    scores.to_pandas().to_csv(ROOT / "ragas_metric_scores.csv", index=False)
    print(f"Saved RAGAS metrics to {ROOT / 'ragas_metric_scores.csv'}")

if __name__ == "__main__":
    main()

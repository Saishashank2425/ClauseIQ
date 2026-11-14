"""Run the 50-question ClauseIQ golden set and optional RAGAS scoring.

Set CLAUSEIQ_BASE_URL to a running ClauseIQ deployment. For LLM-as-judge metrics,
set RAGAS_API_KEY and RAGAS_BASE_URL (Groq-compatible endpoint is supported).
"""
from __future__ import annotations
import json, os, re, time
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "datasets" / "evaluation" / "clauseiq_golden_50.jsonl"
CITATION = re.compile(r"\[(C\d{4})(?:, page (\d+))?\]")

def main() -> None:
    base = os.getenv("CLAUSEIQ_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    cases = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows, citation_ok = [], 0
    with httpx.Client(timeout=90.0) as client:
        for i, case in enumerate(cases, 1):
            response = client.post(base + "/api/v1/demo/ask", json={"question": case["question"]})
            response.raise_for_status()
            result = response.json()
            evidence = result.get("evidence", [])
            citations = CITATION.findall(result.get("answer", ""))
            valid_ids = {item.get("clause_id") for item in evidence}
            valid_pages = {(item.get("clause_id"), str(item.get("page"))) for item in evidence if item.get("page") is not None}
            syntax_valid = bool(citations) and all(cid in valid_ids and (not page or (cid, page) in valid_pages) for cid, page in citations)
            expected_source_retrieved = any(item.get("clause_id") == case["expected_clause_id"] and str(item.get("page")) == str(case["expected_page"]) for item in evidence)
            expected_source_cited = (case["expected_clause_id"], str(case["expected_page"])) in citations
            passed = syntax_valid and expected_source_retrieved and expected_source_cited and not result.get("abstained", False)
            citation_ok += int(passed)
            rows.append({
                "user_input": case["question"],
                "response": result.get("answer", ""),
                "retrieved_contexts": [item.get("text", "") for item in evidence],
                "reference": case["reference_answer"],
                "citation_valid": syntax_valid,
                "expected_source_retrieved": expected_source_retrieved,
                "expected_source_cited": expected_source_cited,
                "abstained": bool(result.get("abstained", False)),
                "provider": result.get("provider"),
                "model": result.get("model"),
                "latency_placeholder": None,
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

    print(f"\nCitation gate: {citation_ok}/{len(rows)} ({citation_ok / max(len(rows), 1):.1%})")
    print(f"Detailed results: {out_csv}")
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

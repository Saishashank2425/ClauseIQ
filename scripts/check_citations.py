"""Offline schema and citation-fixture check for the 50-question golden set."""
import json, re
from pathlib import Path

DATASET = Path(__file__).resolve().parents[1] / "datasets" / "evaluation" / "clauseiq_golden_50.jsonl"
CITATION = re.compile(r"\[(C\d{4})(?:, page (\d+))?\]")

def main():
    rows = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 50, f"Expected 50 evaluation questions, got {len(rows)}"
    for row in rows:
        assert row["question"] and row["reference_answer"] and row["expected_clause_id"]
        assert CITATION.fullmatch(f'[{row["expected_clause_id"]}, page {row["expected_page"]}]')
    print(f"PASS: {len(rows)} golden questions have valid schema and clause/page citation fixtures.")

if __name__ == "__main__":
    main()

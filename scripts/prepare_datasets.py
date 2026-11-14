"""Normalize locally downloaded CUAD/ContractNLI files to JSONL.

This script intentionally does not download datasets or redistribute source data.
Place source files under datasets/raw and follow each source's terms.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any


def walk(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk(value)


def normalize_cuad(source: Path, target: Path) -> int:
    data = json.loads(source.read_text(encoding="utf-8"))
    records = []
    for item in walk(data):
        question = item.get("question") or item.get("category")
        answers = item.get("answers")
        if question and isinstance(answers, dict):
            for answer in answers.get("text", []):
                if isinstance(answer, str) and answer.strip():
                    records.append({"source": "CUAD", "category": str(question), "text": answer.strip()})
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as out:
        for row in records: out.write(json.dumps(row, ensure_ascii=False) + "\\n")
    return len(records)


def normalize_contractnli(source: Path, target: Path) -> int:
    data = json.loads(source.read_text(encoding="utf-8"))
    records = []
    for item in data.get("documents", []):
        doc_id = item.get("id")
        text = "\\n".join(s.get("text", "") for s in item.get("text", []))
        for hypothesis in item.get("labels", []):
            records.append({"source": "ContractNLI", "document_id": doc_id, "text": text,
                            "hypothesis": hypothesis.get("hypothesis"), "label": hypothesis.get("label")})
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as out:
        for row in records: out.write(json.dumps(row, ensure_ascii=False) + "\\n")
    return len(records)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuad", type=Path, help="Path to CUAD JSON source file")
    parser.add_argument("--contractnli", type=Path, help="Path to ContractNLI JSON source file")
    parser.add_argument("--output", type=Path, default=Path("datasets/processed"))
    args = parser.parse_args()
    if not args.cuad and not args.contractnli: parser.error("provide --cuad and/or --contractnli")
    if args.cuad: print(f"CUAD records: {normalize_cuad(args.cuad, args.output / 'cuad.jsonl')}")
    if args.contractnli: print(f"ContractNLI records: {normalize_contractnli(args.contractnli, args.output / 'contractnli.jsonl')}")

if __name__ == "__main__": main()

"""Normalize locally obtained CUAD and ContractNLI releases to JSONL.

No dataset is downloaded or redistributed by this script. Keep source files under
datasets/raw and follow the source dataset's license/terms.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any

def load_json(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return [json.loads(line) for line in text.splitlines() if line.strip()]

def write_jsonl(rows: list[dict], target: Path) -> int:
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as out:
        for row in rows:
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(rows)

def walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)

def normalize_cuad(source: Path, target: Path) -> int:
    data = load_json(source)
    records, seen = [], set()
    for item in walk(data):
        if not isinstance(item, dict) or not item.get("question"):
            continue
        answers = item.get("answers", [])
        category = str(item["question"]).strip()
        if isinstance(answers, dict):
            texts = answers.get("text", [])
        elif isinstance(answers, list):
            texts = [a.get("text", "") if isinstance(a, dict) else str(a) for a in answers]
        else:
            texts = []
        for answer in texts:
            text = str(answer).strip()
            key = (category, text)
            if text and key not in seen:
                seen.add(key)
                records.append({"source": "CUAD", "category": category, "text": text})
    return write_jsonl(records, target)

def normalize_contractnli(source: Path, target: Path) -> int:
    data = load_json(source)
    if isinstance(data, list):
        docs = data
        hypotheses = {}
    else:
        docs = data.get("documents", [])
        hypotheses = data.get("hypotheses", {})
    if isinstance(docs, dict):
        docs = [{"id": key, **value} for key, value in docs.items()]
    if isinstance(hypotheses, list):
        hypotheses = {str(h.get("hypothesis_id", h.get("id", i))): h.get("hypothesis", "") for i, h in enumerate(hypotheses)}
    records = []
    for doc in docs:
        sentences = doc.get("text", [])
        if isinstance(sentences, list):
            full_text = "\n".join(s.get("text", "") if isinstance(s, dict) else str(s) for s in sentences)
        else:
            full_text = str(sentences)
        labels = doc.get("labels", {})
        if isinstance(labels, list):
            label_items = enumerate(labels)
        elif isinstance(labels, dict):
            label_items = labels.items()
        else:
            continue
        for hypothesis_id, annotation in label_items:
            if not isinstance(annotation, dict):
                annotation = {"label": annotation}
            hypothesis = annotation.get("hypothesis") or hypotheses.get(str(hypothesis_id), "")
            label = annotation.get("label") or annotation.get("choice") or annotation.get("gold_label")
            if full_text.strip() and label:
                records.append({"source": "ContractNLI", "document_id": doc.get("id"),
                                "hypothesis_id": str(hypothesis_id), "hypothesis": hypothesis,
                                "label": str(label), "text": full_text.strip()})
    return write_jsonl(records, target)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuad", type=Path)
    parser.add_argument("--contractnli", type=Path)
    parser.add_argument("--output", type=Path, default=Path("datasets/processed"))
    args = parser.parse_args()
    if not args.cuad and not args.contractnli:
        parser.error("provide --cuad and/or --contractnli")
    if args.cuad:
        print(f"CUAD records: {normalize_cuad(args.cuad, args.output / 'cuad.jsonl')}")
    if args.contractnli:
        print(f"ContractNLI records: {normalize_contractnli(args.contractnli, args.output / 'contractnli.jsonl')}")

if __name__ == "__main__":
    main()

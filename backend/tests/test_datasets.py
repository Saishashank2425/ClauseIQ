import json
from pathlib import Path
from scripts.prepare_datasets import normalize_cuad, normalize_contractnli

def test_cuad_squad_style_answers_are_normalized(tmp_path: Path):
    source=tmp_path/"cuad.json"
    source.write_text(json.dumps({"data":[{"paragraphs":[{"qas":[{"question":"Governing Law","answers":[{"text":"New York law applies."}]}]}]}]}),encoding="utf-8")
    target=tmp_path/"cuad.jsonl"
    assert normalize_cuad(source,target)==1
    row=json.loads(target.read_text(encoding="utf-8").splitlines()[0])
    assert row["category"]=="Governing Law"
    assert row["text"]=="New York law applies."

def test_contractnli_documents_and_hypotheses_normalize(tmp_path: Path):
    source=tmp_path/"nli.json"
    source.write_text(json.dumps({"hypotheses":{"h1":"The contract has confidentiality obligations."},"documents":[{"id":"d1","text":[{"text":"The parties shall keep information confidential."}],"labels":{"h1":{"choice":"Entailment"}}}]}),encoding="utf-8")
    target=tmp_path/"nli.jsonl"
    assert normalize_contractnli(source,target)==1
    row=json.loads(target.read_text(encoding="utf-8").splitlines()[0])
    assert row["label"]=="Entailment"
    assert "confidential" in row["text"]

def test_prepare_jsonl_writes_real_newlines(tmp_path: Path):
    source=tmp_path/"cuad.json"
    source.write_text(json.dumps({"data":[{"paragraphs":[{"qas":[{"question":"Term","answers":[{"text":"Thirty days."}]}]}]}]}),encoding="utf-8")
    target=tmp_path/"out.jsonl"
    normalize_cuad(source,target)
    assert len(target.read_text(encoding="utf-8").splitlines())==1

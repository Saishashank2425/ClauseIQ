"""Fine-tune Legal-BERT on normalized CUAD clause-category examples.

Install requirements-ml.txt first. This is a supervised classification experiment;
report macro-F1 and per-class metrics and do not treat its output as legal advice.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, classification_report
from datasets import Dataset
from transformers import (AutoTokenizer, AutoModelForSequenceClassification,
                          DataCollatorWithPadding, Trainer, TrainingArguments)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("datasets/processed/cuad.jsonl"))
    parser.add_argument("--model", default="nlpaueb/legal-bert-base-uncased")
    parser.add_argument("--output", type=Path, default=Path("artifacts/legalbert-clause-classifier"))
    parser.add_argument("--epochs", type=float, default=2)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = [r for r in rows if r.get("text") and r.get("category")]
    labels = sorted({r["category"] for r in rows})
    if len(rows) < 20 or len(labels) < 2:
        raise SystemExit("Need at least 20 labeled examples across at least 2 categories.")
    label_to_id = {label: i for i, label in enumerate(labels)}
    texts = [r["text"] for r in rows]
    y = np.asarray([label_to_id[r["category"]] for r in rows])
    counts = np.bincount(y)
    stratify = y if len(counts) and counts.min() >= 2 else None
    x_train, x_test, y_train, y_test = train_test_split(texts, y, test_size=0.2, random_state=42, stratify=stratify)
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    def make_dataset(x, labels):
        ds = Dataset.from_dict({"text": x, "labels": labels.tolist()})
        return ds.map(lambda batch: tokenizer(batch["text"], truncation=True, max_length=512), batched=True)
    train_ds, test_ds = make_dataset(x_train, y_train), make_dataset(x_test, y_test)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model, num_labels=len(labels), id2label={i: label for label, i in label_to_id.items()},
        label2id=label_to_id
    )
    def metrics(pred):
        logits, gold = pred
        guess = np.argmax(logits, axis=-1)
        return {"accuracy": accuracy_score(gold, guess), "macro_f1": f1_score(gold, guess, average="macro", zero_division=0)}
    training = TrainingArguments(
        output_dir=str(args.output / "checkpoints"), num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size, per_device_eval_batch_size=args.batch_size,
        eval_strategy="epoch", save_strategy="epoch", logging_steps=25,
        load_best_model_at_end=True, metric_for_best_model="macro_f1",
        greater_is_better=True, report_to="none", seed=42
    )
    trainer = Trainer(model=model, args=training, train_dataset=train_ds, eval_dataset=test_ds,
                      tokenizer=tokenizer, data_collator=DataCollatorWithPadding(tokenizer), compute_metrics=metrics)
    trainer.train()
    prediction = trainer.predict(test_ds)
    guesses = np.argmax(prediction.predictions, axis=-1)
    print(classification_report(y_test, guesses, labels=list(range(len(labels))), target_names=labels, zero_division=0))
    args.output.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(args.output)); tokenizer.save_pretrained(str(args.output))
    (args.output / "label_map.json").write_text(json.dumps(label_to_id, indent=2), encoding="utf-8")
    print(f"Saved Legal-BERT model to {args.output}")

if __name__ == "__main__":
    main()

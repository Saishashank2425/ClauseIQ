"""Evaluate a trained classical classifier on labeled JSONL."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import joblib
from sklearn.metrics import accuracy_score,f1_score,classification_report
def main():
    p=argparse.ArgumentParser();p.add_argument("--input",type=Path,default=Path("datasets/processed/cuad.jsonl"));p.add_argument("--model",type=Path,default=Path("artifacts/clause_classifier.joblib"));p.add_argument("--mlflow",action="store_true");a=p.parse_args()
    rows=[json.loads(x) for x in a.input.read_text(encoding="utf-8").splitlines() if x.strip()]
    rows=[r for r in rows if r.get("text") and r.get("category")]
    model=joblib.load(a.model);x=[r["text"] for r in rows];y=[r["category"] for r in rows];pred=model.predict(x)
    metrics={"accuracy":float(accuracy_score(y,pred)),"macro_f1":float(f1_score(y,pred,average="macro",zero_division=0))}
    print(classification_report(y,pred,zero_division=0));print(json.dumps(metrics,indent=2))
    if a.mlflow:
        import mlflow
        with mlflow.start_run():mlflow.log_metrics(metrics)
if __name__=="__main__":main()

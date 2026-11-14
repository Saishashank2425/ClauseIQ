"""Train/evaluate a reproducible CUAD clause-category baseline.
Input: JSONL produced by scripts/prepare_datasets.py (category, text).
The trained artifact is local and must not be committed.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

def main():
 p=argparse.ArgumentParser();p.add_argument("--input",type=Path,default=Path("datasets/processed/cuad.jsonl"));p.add_argument("--output",type=Path,default=Path("artifacts/clause_classifier.joblib"));a=p.parse_args()
 rows=[json.loads(line) for line in a.input.read_text(encoding="utf-8").splitlines() if line.strip()]
 rows=[r for r in rows if r.get("text") and r.get("category")]
 labels={r["category"] for r in rows}
 if len(rows)<10 or len(labels)<2: raise SystemExit("Need at least 10 labeled examples across 2+ categories.")
 X=[r["text"] for r in rows];y=[r["category"] for r in rows]
 counts={label:y.count(label) for label in labels}
 stratify=y if min(counts.values())>=2 else None
 X_train,X_test,y_train,y_test=train_test_split(X,y,test_size=0.2,random_state=42,stratify=stratify)
 model=Pipeline([("tfidf",TfidfVectorizer(ngram_range=(1,2),min_df=1,max_features=200000,sublinear_tf=True)),("classifier",LinearSVC(class_weight="balanced"))])
 model.fit(X_train,y_train);pred=model.predict(X_test)
 print(classification_report(y_test,pred,zero_division=0))
 a.output.parent.mkdir(parents=True,exist_ok=True);joblib.dump(model,a.output)
 print(f"Saved model: {a.output} (train={len(X_train)}, test={len(X_test)}, labels={len(labels)})")
if __name__=="__main__":main()

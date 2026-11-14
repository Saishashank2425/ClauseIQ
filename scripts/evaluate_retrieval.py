"""Evaluate Recall@k and MRR@k from JSONL query/document examples."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from backend.app.retrieval.hybrid import HybridRetriever
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--k",type=int,default=5)
    p.add_argument("--mlflow",action="store_true")
    a=p.parse_args()
    rows=[json.loads(line) for line in a.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows=[r for r in rows if r.get("query") and r.get("documents") and r.get("relevant_indices") is not None]
    if not rows: raise SystemExit("Rows need query, documents (passages), and relevant_indices (integer positions).")
    hits=[]; rr=[]
    for row in rows:
        ranked=[i for i,_ in HybridRetriever(row["documents"]).search(row["query"],top_k=a.k)]
        relevant=set(row["relevant_indices"])
        hits.append(float(bool(relevant.intersection(ranked))))
        rank=next((n for n,i in enumerate(ranked,1) if i in relevant),None)
        rr.append(1/rank if rank else 0.0)
    metrics={"recall_at_k":sum(hits)/len(hits),"mrr_at_k":sum(rr)/len(rr),"queries":len(rows),"k":a.k}
    print(json.dumps(metrics,indent=2))
    if a.mlflow:
        import mlflow
        with mlflow.start_run():
            mlflow.log_params({"k":a.k,"queries":len(rows)})
            mlflow.log_metrics({"recall_at_k":metrics["recall_at_k"],"mrr_at_k":metrics["mrr_at_k"]})
if __name__=="__main__": main()

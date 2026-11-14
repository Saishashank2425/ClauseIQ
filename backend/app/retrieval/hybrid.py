"""Hybrid BM25 + TF-IDF retrieval with optional cross-encoder reranking.
TF-IDF is a sparse vector-space baseline, not a neural embedding model.
"""
from __future__ import annotations
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from backend.app.retrieval.bm25 import BM25Index

class HybridRetriever:
 def __init__(self, documents: list[str]):
  self.documents=documents
  self.bm25=BM25Index(documents)
  self.vectorizer=TfidfVectorizer(ngram_range=(1,2),sublinear_tf=True)
  try:self.matrix=self.vectorizer.fit_transform(documents)
  except ValueError:self.matrix=None
  self.cross_encoder=None
  model_name=os.getenv("CLAUSEIQ_CROSS_ENCODER_MODEL")
  if model_name:
   try:
    from sentence_transformers import CrossEncoder
    self.cross_encoder=CrossEncoder(model_name)
   except Exception:
    self.cross_encoder=None

 def search(self, query: str, top_k: int=5) -> list[tuple[int,float]]:
  if not self.documents:return []
  bm=self.bm25.search(query,top_k=len(self.documents))
  bm_scores={i:s for i,s in bm}; max_bm=max(bm_scores.values(),default=0.0) or 1.0
  vector_scores={}
  if self.matrix is not None:
   q=self.vectorizer.transform([query])
   vector_scores={i:float(v) for i,v in enumerate(cosine_similarity(q,self.matrix)[0])}
  combined=[]
  for i in range(len(self.documents)):
   bm_norm=bm_scores.get(i,0.0)/max_bm
   tfidf=vector_scores.get(i,0.0)
   score=0.55*bm_norm+0.45*tfidf
   if score>0:combined.append((i,score))
  combined.sort(key=lambda x:x[1],reverse=True)
  candidates=combined[:max(top_k*3,top_k)]
  if self.cross_encoder and candidates:
   pairs=[(query,self.documents[i]) for i,_ in candidates]
   try:
    scores=self.cross_encoder.predict(pairs)
    candidates=[(candidates[j][0],float(scores[j])) for j in range(len(candidates))]
    candidates.sort(key=lambda x:x[1],reverse=True)
   except Exception:pass
  return candidates[:top_k]

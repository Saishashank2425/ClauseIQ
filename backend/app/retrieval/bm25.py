"""Dependency-free BM25 retrieval for clause-sized text passages."""
from __future__ import annotations
import math, re
from collections import Counter

TOKEN = re.compile(r"[a-zA-Z0-9_]+")

def tokenize(text: str) -> list[str]:
    return TOKEN.findall(text.lower())

class BM25Index:
    def __init__(self, documents: list[str], k1: float = 1.5, b: float = 0.75):
        self.documents = documents
        self.tokens = [tokenize(d) for d in documents]
        self.k1, self.b = k1, b
        self.avgdl = sum(map(len, self.tokens)) / max(len(self.tokens), 1)
        self.lengths = [len(t) for t in self.tokens]
        self.df: Counter[str] = Counter()
        self.tf = []
        for tokens in self.tokens:
            counts = Counter(tokens); self.tf.append(counts)
            self.df.update(counts.keys())

    def search(self, query: str, top_k: int = 5) -> list[tuple[int, float]]:
        terms = set(tokenize(query)); n = len(self.documents); scores = []
        for index, counts in enumerate(self.tf):
            score = 0.0
            for term in terms:
                frequency = counts.get(term, 0)
                if not frequency: continue
                df = self.df[term]
                idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
                denom = frequency + self.k1 * (1 - self.b + self.b * self.lengths[index] / max(self.avgdl, 1))
                score += idf * frequency * (self.k1 + 1) / denom
            if score > 0: scores.append((index, score))
        return sorted(scores, key=lambda pair: pair[1], reverse=True)[:top_k]

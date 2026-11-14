"""Lazy inference for the classical baseline or an optional fine-tuned Legal-BERT."""
from __future__ import annotations
import os
from pathlib import Path
import joblib
ROOT = Path(__file__).resolve().parents[3]
CLASSICAL_PATH = ROOT / "artifacts" / "clause_classifier.joblib"
LEGALBERT_PATH = Path(os.getenv("CLAUSEIQ_LEGALBERT_PATH", str(ROOT / "artifacts" / "legalbert-clause-classifier")))
_MODEL = None
_BACKEND = None
_ATTEMPTED = False
def load_model():
    global _MODEL, _BACKEND, _ATTEMPTED
    if _ATTEMPTED: return _MODEL
    _ATTEMPTED = True
    if os.getenv("CLAUSEIQ_CLASSIFIER_BACKEND", "classical").lower() == "legalbert" and LEGALBERT_PATH.exists():
        try:
            from transformers import pipeline
            _MODEL = pipeline("text-classification", model=str(LEGALBERT_PATH), tokenizer=str(LEGALBERT_PATH), truncation=True)
            _BACKEND = "legalbert"
            return _MODEL
        except Exception: _MODEL = None
    if CLASSICAL_PATH.exists():
        try:
            _MODEL = joblib.load(CLASSICAL_PATH)
            _BACKEND = "classical"
        except Exception: _MODEL = None
    return _MODEL
def predict_clause_category(text: str) -> str | None:
    model = load_model()
    if model is None or not text.strip(): return None
    try:
        if _BACKEND == "legalbert": return str(model(text[:12000])[0]["label"])
        return str(model.predict([text])[0])
    except Exception: return None

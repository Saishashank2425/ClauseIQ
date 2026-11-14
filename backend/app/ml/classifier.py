"""Optional trained TF-IDF + LinearSVC clause classifier."""
from __future__ import annotations
from pathlib import Path
import joblib

MODEL_PATH = Path(__file__).resolve().parents[3] / "artifacts" / "clause_classifier.joblib"
_MODEL = None
_ATTEMPTED = False

def load_model():
    global _MODEL, _ATTEMPTED
    if not _ATTEMPTED:
        _ATTEMPTED = True
        if MODEL_PATH.exists():
            try: _MODEL = joblib.load(MODEL_PATH)
            except Exception: _MODEL = None
    return _MODEL

def predict_clause_category(text: str) -> str | None:
    model = load_model()
    if model is None or not text.strip(): return None
    try: return str(model.predict([text])[0])
    except Exception: return None

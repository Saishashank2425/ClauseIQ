from unittest.mock import patch

from backend.app.observability import update_observation
from backend.app.rag.answer import _record_answer_observation


class FakeObservation:
    def __init__(self):
        self.payload = None

    def update(self, **kwargs):
        self.payload = kwargs


def test_langfuse_observation_accepts_only_allowlisted_metric_fields():
    span = FakeObservation()

    update_observation(span, {
        "mode": "grounded_llm",
        "abstained": False,
        "latencyMs": 127.5,
        "question": "confidential user question",
        "answer": "confidential generated answer",
        "contractText": "private clause passage",
    })

    assert span.payload == {
        "metadata": {
            "mode": "grounded_llm",
            "abstained": False,
            "latencyMs": 127.5,
        }
    }


def test_answer_observation_records_operational_metrics_without_answer_text():
    span = object()
    result = {
        "mode": "grounded_llm",
        "abstained": False,
        "answer": "Sensitive contract response",
        "latency_ms": 325.4,
        "retrieval_coverage": 0.875,
        "provider": "provider-a",
        "model": "model-a",
        "usage": {
            "prompt_tokens": 110,
            "completion_tokens": 34,
            "total_tokens": 144,
        },
    }

    with patch("backend.app.rag.answer.update_observation") as update:
        _record_answer_observation(span, result)

    recorded_span, metadata = update.call_args.args
    assert recorded_span is span
    assert metadata == {
        "mode": "grounded_llm",
        "abstained": False,
        "citationValid": True,
        "latencyMs": 325.4,
        "retrievalCoverage": 0.875,
        "provider": "provider-a",
        "model": "model-a",
        "inputTokens": 110,
        "outputTokens": 34,
        "totalTokens": 144,
    }
    assert "answer" not in metadata

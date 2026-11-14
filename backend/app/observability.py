"""Optional Langfuse tracing with privacy-safe defaults."""
from __future__ import annotations
import logging, os
from contextlib import contextmanager
from typing import Any, Iterator

logger = logging.getLogger(__name__)

@contextmanager
def trace_observation(name: str, metadata: dict[str, Any] | None = None) -> Iterator[Any]:
    """Create a Langfuse span when configured; tracing failures never break requests.

    Raw questions, contract passages, and generated answers are intentionally excluded.
    """
    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        yield None
        return
    try:
        from langfuse import get_client
        client = get_client()
        safe_metadata = {str(k): str(v)[:180] for k, v in (metadata or {}).items() if v is not None}
        observation = client.start_as_current_observation(as_type="span", name=name, metadata=safe_metadata)
    except Exception as exc:
        logger.warning("Langfuse tracing unavailable (%s); continuing without tracing", type(exc).__name__)
        yield None
        return
    with observation as span:
        yield span

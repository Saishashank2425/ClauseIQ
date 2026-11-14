"""Free-tier, OpenAI-compatible provider failover for ClauseIQ."""
from __future__ import annotations
import logging, os, time
from dataclasses import dataclass
from typing import Any
import httpx

logger = logging.getLogger(__name__)
TRANSIENT = {408, 429, 500, 502, 503, 504}

@dataclass(frozen=True)
class Provider:
    name: str
    base_url: str
    model: str
    api_key: str

def configured_providers() -> list[Provider]:
    configs = {
        "groq": Provider("groq", os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").strip().rstrip("/"), os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip(), os.getenv("GROQ_API_KEY", "").strip()),
        "gemini": Provider("gemini", os.getenv("CLAUSEIQ_LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai").strip().rstrip("/"), os.getenv("CLAUSEIQ_LLM_MODEL", "").strip(), os.getenv("CLAUSEIQ_LLM_API_KEY", "").strip()),
        "cerebras": Provider("cerebras", os.getenv("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1").strip().rstrip("/"), os.getenv("CEREBRAS_MODEL", "").strip(), os.getenv("CEREBRAS_API_KEY", "").strip()),
    }
    order = [name.strip().lower() for name in os.getenv("CLAUSEIQ_LLM_PROVIDER_ORDER", "groq,gemini,cerebras").split(",")]
    return [configs[name] for name in order if name in configs and configs[name].api_key and configs[name].model and configs[name].base_url]

def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "\n".join(block["text"] for block in content if isinstance(block, dict) and isinstance(block.get("text"), str)).strip()
    return ""

def generate(messages: list[dict[str, str]], *, max_tokens: int = 700) -> dict[str, Any]:
    providers = configured_providers()
    if not providers:
        return {"text": None, "status": "no_free_provider_configured", "provider": None, "model": None, "usage": {}}
    failures: list[str] = []
    for provider in providers:
        for attempt in range(2):
            try:
                response = httpx.post(
                    f"{provider.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {provider.api_key}", "Content-Type": "application/json"},
                    json={"model": provider.model, "temperature": 0, "max_tokens": max_tokens, "messages": messages},
                    timeout=httpx.Timeout(22.0, connect=8.0),
                )
                if response.status_code in TRANSIENT and attempt == 0:
                    retry_after = response.headers.get("Retry-After", "")
                    try:
                        delay = min(max(float(retry_after), 0.5), 2.0) if retry_after else 1.0
                    except ValueError:
                        delay = 1.0
                    logger.warning("LLM provider %s returned HTTP %s; retrying once", provider.name, response.status_code)
                    time.sleep(delay)
                    continue
                if response.is_error:
                    failures.append(f"{provider.name}:http_{response.status_code}")
                    logger.warning("LLM provider %s failed with HTTP %s; trying next provider", provider.name, response.status_code)
                    break
                data = response.json()
                choices = data.get("choices", []) if isinstance(data, dict) else []
                message = choices[0].get("message", {}) if choices else {}
                text = _content_text(message.get("content") if isinstance(message, dict) else None)
                if not text:
                    failures.append(f"{provider.name}:empty_response")
                    break
                usage = data.get("usage", {}) if isinstance(data, dict) else {}
                return {
                    "text": text, "status": "ok", "provider": provider.name, "model": provider.model,
                    "usage": {"prompt_tokens": int(usage.get("prompt_tokens", 0) or 0), "completion_tokens": int(usage.get("completion_tokens", 0) or 0), "total_tokens": int(usage.get("total_tokens", 0) or 0)},
                }
            except httpx.TimeoutException:
                failures.append(f"{provider.name}:timeout")
                logger.warning("LLM provider %s timed out; trying next provider", provider.name)
                break
            except (httpx.RequestError, ValueError, TypeError, KeyError, IndexError) as exc:
                failures.append(f"{provider.name}:{type(exc).__name__}")
                logger.warning("LLM provider %s request failed (%s); trying next provider", provider.name, type(exc).__name__)
                break
    logger.error("No configured LLM provider produced a response; failures=%s", ",".join(failures))
    return {"text": None, "status": "all_providers_unavailable", "provider": None, "model": None, "usage": {}, "failures": failures}

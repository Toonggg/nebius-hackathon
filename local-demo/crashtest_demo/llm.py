"""Minimal Token Factory chat client (OpenAI-compatible), standard library only.

It's stdlib-only so the same code runs on a laptop and inside a Sandboxes image without extra
dependencies. Every call is reported to ``on_call`` (model, latency, tokens) so the agent can
log it as an ``llm_call`` event.
"""

import json
import os
import time
import urllib.error
import urllib.request

BASE_URL = os.environ.get("TOKEN_FACTORY_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")
MODEL_REASONING = os.environ.get("MODEL_REASONING", "nvidia/Nemotron-3-Ultra-550b-a55b")  # hypotheses
MODEL_MAIN = os.environ.get("MODEL_MAIN", "nvidia/nemotron-3-super-120b-a12b")  # per-step decisions


class LLMError(RuntimeError):
    pass


def chat_json(model, system, user, schema, *, name="reply", max_tokens=4000, timeout=180, on_call=None):
    """One chat completion constrained to ``schema``; returns the parsed JSON object.

    Raises LLMError on HTTP errors, timeouts, or a reply that isn't JSON. Schema *validation*
    is the caller's job: Python re-checks every value the planner uses.
    """
    key = os.environ.get("NEBIUS_API_KEY")
    if not key:
        raise LLMError("NEBIUS_API_KEY is not set")
    body = {
        "model": model,
        "temperature": 0,
        "max_tokens": max_tokens,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "response_format": {"type": "json_schema", "json_schema": {"name": name, "schema": schema}},
    }
    req = urllib.request.Request(
        BASE_URL.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as err:
        raise LLMError(f"HTTP {err.code}: {err.read().decode(errors='replace')[:300]}") from None
    except (urllib.error.URLError, TimeoutError) as err:
        raise LLMError(f"request failed: {err}") from None
    latency = round(time.time() - t0, 2)
    usage = data.get("usage") or {}
    if on_call:
        on_call(model=data.get("model", model), latency_s=latency,
                prompt_tokens=usage.get("prompt_tokens"), completion_tokens=usage.get("completion_tokens"))
    content = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
    try:
        return json.loads(_strip_fences(content))
    except ValueError:
        raise LLMError(f"reply is not JSON: {content[:200]!r}") from None


def _strip_fences(text):
    """Some models wrap JSON in ```json fences even with response_format set."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    return text

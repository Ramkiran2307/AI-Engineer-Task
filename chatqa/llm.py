"""Small provider-neutral LLM client that returns parsed JSON.

Providers (pick with LLM_PROVIDER, or it is auto-detected from which key is set):
  groq      OpenAI-compatible, https://api.groq.com/openai/v1      key: GROQ_API_KEY / LLM_API_KEY
  gemini    OpenAI-compatible, Google's /v1beta/openai endpoint      key: GEMINI_API_KEY / LLM_API_KEY
  openai    any OpenAI-compatible endpoint (set LLM_BASE_URL)        key: OPENAI_API_KEY / LLM_API_KEY
  ollama    local, http://localhost:11434/v1                         no key
  anthropic Claude via the official `anthropic` SDK                  key: ANTHROPIC_API_KEY
Override the model with LLM_MODEL and the endpoint with LLM_BASE_URL.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass

import requests

PRESETS = {
    "groq": {"base_url": "https://api.groq.com/openai/v1", "model": "llama-3.3-70b-versatile", "key_env": "GROQ_API_KEY"},
    "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai", "model": "gemini-2.5-flash", "key_env": "GEMINI_API_KEY"},
    "openai": {"base_url": "https://api.openai.com/v1", "model": None, "key_env": "OPENAI_API_KEY"},
    "ollama": {"base_url": "http://localhost:11434/v1", "model": "qwen2.5:7b", "key_env": None},
    "anthropic": {"base_url": None, "model": "claude-opus-5-5", "key_env": "ANTHROPIC_API_KEY"},
}


class LLMError(RuntimeError):
    pass


@dataclass
class LLMConfig:
    provider: str
    model: str
    base_url: str | None
    api_key: str | None

    def label(self) -> str:
        return f"{self.provider}:{self.model}"


def config_from_env(provider: str | None = None, model: str | None = None) -> LLMConfig | None:
    """Build a config from env vars. Returns None if no provider is usable."""
    provider = (provider or os.getenv("LLM_PROVIDER") or "").strip().lower()
    if not provider:
        for name in ("anthropic", "groq", "gemini", "openai"):
            if os.getenv(PRESETS[name]["key_env"]):
                provider = name
                break
    if not provider:
        if os.getenv("LLM_API_KEY") and os.getenv("LLM_BASE_URL"):
            provider = "openai"
        else:
            return None
    if provider not in PRESETS:
        raise LLMError(f"Unknown LLM_PROVIDER '{provider}'. Choose one of: {', '.join(PRESETS)}")
    preset = PRESETS[provider]
    key = os.getenv("LLM_API_KEY") or (os.getenv(preset["key_env"]) if preset["key_env"] else None)
    if preset["key_env"] and not key:
        raise LLMError(f"LLM_PROVIDER={provider} needs an API key: set {preset['key_env']} or LLM_API_KEY in .env")
    model = model or os.getenv("LLM_MODEL") or preset["model"]
    if not model:
        raise LLMError(f"LLM_PROVIDER={provider} needs LLM_MODEL to be set")
    base_url = os.getenv("LLM_BASE_URL") or preset["base_url"]
    return LLMConfig(provider=provider, model=model, base_url=base_url, api_key=key)


def extract_json(text: str) -> dict:
    """Parse a JSON object out of model output (tolerates ```json fences and chatter)."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise


class LLM:
    """complete_json(system, context, prompt, schema) -> dict

    `context` is the large, stable part (the chat); `prompt` is the small, varying
    part (the question). Keeping them apart lets providers cache the context.
    """

    def __init__(self, cfg: LLMConfig, verbose: bool = False):
        self.cfg = cfg
        self.verbose = verbose
        self.calls = 0
        self._anthropic = None

    # ---- public -------------------------------------------------------------
    def complete_json(self, system: str, context: str, prompt: str, schema: dict, max_tokens: int = 4000) -> dict:
        last_err = None
        extra = ""
        for attempt in range(2):  # one retry if the JSON is malformed
            text = self._complete(system, context, prompt + extra, schema, max_tokens)
            try:
                data = extract_json(text)
                if not isinstance(data, dict):
                    raise ValueError("top-level JSON is not an object")
                missing = [k for k in schema.get("required", []) if k not in data]
                if missing:
                    raise ValueError(f"missing keys {missing}")
                return data
            except (json.JSONDecodeError, ValueError) as e:
                last_err = e
                extra = (f"\n\nYour previous reply was not valid JSON for the schema ({e}). "
                         "Reply again with ONLY one JSON object matching the schema.")
        raise LLMError(f"Model did not return valid JSON after retry: {last_err}")

    # ---- providers ----------------------------------------------------------
    def _complete(self, system, context, prompt, schema, max_tokens) -> str:
        self.calls += 1
        if self.cfg.provider == "anthropic":
            return self._anthropic_complete(system, context, prompt, schema, max_tokens)
        return self._openai_complete(system, context, prompt, schema, max_tokens)

    def _openai_complete(self, system, context, prompt, schema, max_tokens) -> str:
        url = self.cfg.base_url.rstrip("/") + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.cfg.api_key:
            headers["Authorization"] = f"Bearer {self.cfg.api_key}"
        schema_hint = "\n\nReply with ONLY a JSON object that follows this JSON schema:\n" + json.dumps(schema)
        body = {
            "model": self.cfg.model,
            "temperature": 0,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system + schema_hint},
                {"role": "user", "content": (context + "\n\n" if context else "") + prompt},
            ],
        }
        for attempt in range(8):
            try:
                r = requests.post(url, headers=headers, json=body, timeout=180)
            except requests.RequestException as e:
                if attempt >= 2:
                    raise LLMError(f"Network error calling {url}: {e}") from e
                time.sleep(3)
                continue
            if r.status_code == 429 or r.status_code >= 500:
                wait = _retry_after(r, attempt)
                self._log(f"{r.status_code} from provider, waiting {wait:.0f}s (attempt {attempt + 1})")
                time.sleep(wait)
                continue
            if r.status_code == 400 and "response_format" in r.text and "response_format" in body:
                body.pop("response_format")  # some endpoints don't support JSON mode
                continue
            if r.status_code >= 400:
                raise LLMError(f"{self.cfg.provider} returned HTTP {r.status_code}: {r.text[:500]}")
            data = r.json()
            try:
                return data["choices"][0]["message"]["content"] or ""
            except (KeyError, IndexError) as e:
                raise LLMError(f"Unexpected response shape: {str(data)[:300]}") from e
        raise LLMError("Gave up after repeated rate-limit/server errors")

    def _anthropic_complete(self, system, context, prompt, schema, max_tokens) -> str:
        try:
            import anthropic
        except ImportError as e:
            raise LLMError("LLM_PROVIDER=anthropic needs `pip install anthropic`") from e
        if self._anthropic is None:
            self._anthropic = anthropic.Anthropic(api_key=self.cfg.api_key)
        system_blocks = [{"type": "text", "text": system}]
        if context:
            # The chat is the big stable prefix: cache it across questions.
            system_blocks.append({"type": "text", "text": context, "cache_control": {"type": "ephemeral"}})
        try:
            resp = self._anthropic.beta.messages.create(
                model=self.cfg.model,
                max_tokens=max(max_tokens, 16000),
                system=system_blocks,
                messages=[{"role": "user", "content": prompt}],
                output_config={
                    "effort": os.getenv("LLM_EFFORT", "medium"),
                    "format": {"type": "json_schema", "schema": schema},
                },
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.RateLimitError as e:
            raise LLMError(f"Anthropic rate limit: {e}") from e
        except anthropic.APIStatusError as e:
            raise LLMError(f"Anthropic API error {e.status_code}: {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise LLMError(f"Could not reach the Anthropic API: {e}") from e
        if resp.stop_reason == "refusal":
            raise LLMError("The model declined this request (refusal).")
        if resp.stop_reason == "max_tokens":
            raise LLMError("The model ran out of output tokens.")
        return next((b.text for b in resp.content if b.type == "text"), "")

    def _log(self, msg: str):
        if self.verbose:
            print(f"[llm] {msg}", file=sys.stderr)


def _retry_after(r: requests.Response, attempt: int) -> float:
    h = r.headers.get("retry-after")
    if h:
        try:
            return min(float(h) + 0.5, 90)
        except ValueError:
            pass
    m = re.search(r"try again in (?:(\d+)m)?([\d.]+)s", r.text)
    if m:
        return min(int(m.group(1) or 0) * 60 + float(m.group(2)) + 0.5, 90)
    return min(2 ** attempt * 2, 60)

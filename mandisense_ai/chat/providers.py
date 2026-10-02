"""
LLM providers for the chatbots.

One small interface, three back ends:

* Anthropic (Claude)           -- ANTHROPIC_API_KEY
* Groq (OpenAI-compatible)     -- GROQ_API_KEY
* OpenAI (or any compatible)   -- OPENAI_API_KEY (+ optional OPENAI_BASE_URL)

`CHAT_PROVIDER` forces one (anthropic | groq | openai | none); otherwise the
first key found wins, in that order. `CHAT_MODEL` overrides the default model.
With no key the engine runs its tool-driven fallback, so the chatbots always
work; the key only upgrades the quality of language and reasoning.

Messages use one internal shape:
    {"role": "user" | "assistant" | "tool", "content": str,
     "tool_calls": [{"id", "name", "args"}]   # assistant turns that call tools
     "tool_call_id": str, "name": str}        # tool results
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

try:  # pick up the project .env when run outside uvicorn's env loading
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass


@dataclass
class ToolCall:
    id: str
    name: str
    args: Dict[str, Any]


@dataclass
class LLMResult:
    text: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)


class LLMError(RuntimeError):
    pass


class Provider(ABC):
    name: str
    model: str

    @abstractmethod
    def complete(self, system: str, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]], max_tokens: int = 1100) -> LLMResult:
        ...


def _tool_specs(tools) -> List[Dict[str, Any]]:
    return [{"name": t.name, "description": t.description, "parameters": t.parameters} for t in tools]


class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str):
        self.api_key, self.model = api_key, model

    def complete(self, system, messages, tools, max_tokens=1100) -> LLMResult:
        wire: List[Dict[str, Any]] = []
        for m in messages:
            if m["role"] == "user":
                wire.append({"role": "user", "content": m["content"]})
            elif m["role"] == "assistant":
                blocks: List[Dict[str, Any]] = []
                if m.get("content"):
                    blocks.append({"type": "text", "text": m["content"]})
                for c in m.get("tool_calls", []):
                    blocks.append({"type": "tool_use", "id": c["id"], "name": c["name"], "input": c["args"]})
                wire.append({"role": "assistant", "content": blocks or m.get("content", "")})
            elif m["role"] == "tool":
                block = {"type": "tool_result", "tool_use_id": m["tool_call_id"], "content": m["content"]}
                if wire and wire[-1]["role"] == "user" and isinstance(wire[-1]["content"], list):
                    wire[-1]["content"].append(block)  # parallel tool results share one user turn
                else:
                    wire.append({"role": "user", "content": [block]})
        body: Dict[str, Any] = {"model": self.model, "max_tokens": max_tokens, "system": system, "messages": wire}
        if tools:
            body["tools"] = [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in _tool_specs(tools)]
        try:
            r = httpx.post("https://api.anthropic.com/v1/messages", json=body, timeout=60,
                           headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        except httpx.HTTPError as exc:
            raise LLMError(f"anthropic network error: {type(exc).__name__}") from exc
        if r.status_code >= 400:
            raise LLMError(f"anthropic HTTP {r.status_code}: {r.text[:200]}")
        out = LLMResult()
        for block in r.json().get("content", []):
            if block["type"] == "text":
                out.text += block["text"]
            elif block["type"] == "tool_use":
                out.tool_calls.append(ToolCall(block["id"], block["name"], block.get("input") or {}))
        return out


class OpenAICompatProvider(Provider):
    def __init__(self, name: str, api_key: str, model: str, base_url: str):
        self.name, self.api_key, self.model, self.base_url = name, api_key, model, base_url.rstrip("/")

    def complete(self, system, messages, tools, max_tokens=1100) -> LLMResult:
        wire: List[Dict[str, Any]] = [{"role": "system", "content": system}]
        for m in messages:
            if m["role"] == "user":
                wire.append({"role": "user", "content": m["content"]})
            elif m["role"] == "assistant":
                msg: Dict[str, Any] = {"role": "assistant", "content": m.get("content") or None}
                if m.get("tool_calls"):
                    msg["tool_calls"] = [{"id": c["id"], "type": "function",
                                          "function": {"name": c["name"], "arguments": json.dumps(c["args"], ensure_ascii=False)}}
                                         for c in m["tool_calls"]]
                wire.append(msg)
            elif m["role"] == "tool":
                wire.append({"role": "tool", "tool_call_id": m["tool_call_id"], "content": m["content"]})
        body: Dict[str, Any] = {"model": self.model, "messages": wire, "max_tokens": max_tokens, "temperature": 0.2}
        if tools:
            body["tools"] = [{"type": "function", "function": t} for t in _tool_specs(tools)]
            body["tool_choice"] = "auto"
        try:
            r = httpx.post(f"{self.base_url}/chat/completions", json=body, timeout=60,
                           headers={"Authorization": f"Bearer {self.api_key}", "content-type": "application/json"})
        except httpx.HTTPError as exc:
            raise LLMError(f"{self.name} network error: {type(exc).__name__}") from exc
        if r.status_code >= 400:
            raise LLMError(f"{self.name} HTTP {r.status_code}: {r.text[:200]}")
        msg = r.json()["choices"][0]["message"]
        out = LLMResult(text=msg.get("content") or "")
        for c in msg.get("tool_calls") or []:
            try:
                args = json.loads(c["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            out.tool_calls.append(ToolCall(c["id"], c["function"]["name"], args))
        return out


def get_provider() -> Optional[Provider]:
    """The configured LLM, or None (the engine then runs its tool-driven fallback)."""
    choice = os.getenv("CHAT_PROVIDER", "auto").strip().lower()
    model = os.getenv("CHAT_MODEL", "").strip()
    if choice == "none":
        return None
    anth, groq, oai = (os.getenv(k, "").strip() for k in ("ANTHROPIC_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY"))
    if anth and choice in ("auto", "anthropic"):
        return AnthropicProvider(anth, model or "claude-sonnet-5-5")
    if groq and choice in ("auto", "groq"):
        return OpenAICompatProvider("groq", groq, model or "llama-3.3-70b-versatile", "https://api.groq.com/openai/v1")
    if oai and choice in ("auto", "openai"):
        return OpenAICompatProvider("openai", oai, model or "gpt-4o-mini", os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    return None

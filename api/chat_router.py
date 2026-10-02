"""
Chat API for the farmer and trader chatbots.

    POST /v1/chat          one question, one reply (history and context in the body)
    GET  /v1/chat/status   which model is active and what tools each persona has

The work is in `mandisense_ai/chat/`; this file only validates input and
isolates the blocking tool and network calls from the event loop.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/chat", tags=["chat"])


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=2000)


class ChatContext(BaseModel):
    district: Optional[str] = Field(None, max_length=40)
    crop: Optional[str] = Field(None, max_length=40)
    mandi_id: Optional[str] = Field(None, max_length=60)
    last_entities: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    persona: Literal["farmer", "trader"] = "farmer"
    message: str = Field(..., min_length=1, max_length=1000)
    lang: Literal["en", "kn", "hi"] = "en"
    history: List[ChatTurn] = Field(default_factory=list, max_length=20)
    context: ChatContext = Field(default_factory=ChatContext)


@router.post("")
async def chat(req: ChatRequest) -> Dict[str, Any]:
    from mandisense_ai.chat import handle

    return await run_in_threadpool(
        handle,
        req.persona,
        req.message,
        req.lang,
        [t.model_dump() for t in req.history],
        req.context.model_dump(),
    )


@router.get("/status")
async def status() -> Dict[str, Any]:
    from mandisense_ai.chat.providers import get_provider
    from mandisense_ai.chat.tools import tools_for

    provider = get_provider()
    return {
        "mode": "llm" if provider else "tools",
        "provider": provider.name if provider else None,
        "model": provider.model if provider else None,
        "languages": ["en", "kn", "hi"],
        "web_search": True,
        "tools": {p: [t.name for t in tools_for(p)] for p in ("farmer", "trader")},
    }

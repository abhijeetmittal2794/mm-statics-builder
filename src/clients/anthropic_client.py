"""Thin wrapper around the Anthropic SDK for the reasoning agents."""
from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Optional

from anthropic import Anthropic
from anthropic.types import MessageParam

_client: Optional[Anthropic] = None


def client() -> Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set. Copy .env.example to .env.")
        _client = Anthropic(api_key=api_key)
    return _client


def _model() -> str:
    return os.environ.get("CLAUDE_MODEL", "claude-opus-4-5")


def _image_block(path: Path) -> dict:
    """Return an Anthropic image content block from a local file."""
    suffix = path.suffix.lower().lstrip(".")
    media_type = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "gif": "image/gif",
    }.get(suffix, "image/png")
    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": data},
    }


def call_claude(
    *,
    system: str,
    user_text: str,
    image_paths: list[Path] | None = None,
    max_tokens: int = 4000,
    temperature: float = 0.4,
) -> str:
    """One-shot text completion. Returns the assistant's raw text."""
    content: list[dict] = []
    for p in image_paths or []:
        content.append(_image_block(p))
    content.append({"type": "text", "text": user_text})

    messages: list[MessageParam] = [{"role": "user", "content": content}]
    resp = client().messages.create(
        model=_model(),
        system=system,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    return "\n".join(parts).strip()

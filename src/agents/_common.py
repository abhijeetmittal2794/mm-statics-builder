"""Shared helpers for agents: JSON extraction, prompt preambles."""
from __future__ import annotations

import json
import re
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def extract_json(text: str) -> dict:
    """Pull the first JSON object out of a response (handles ```json fences)."""
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        return json.loads(fence.group(1))
    brace = re.search(r"(\{.*\})", text, re.DOTALL)
    if brace:
        return json.loads(brace.group(1))
    raise ValueError(f"No JSON object found in response:\n{text[:500]}")


def parse_model(text: str, model: Type[T]) -> T:
    try:
        data = extract_json(text)
        return model.model_validate(data)
    except (ValidationError, ValueError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Failed to parse {model.__name__}: {e}\n\nRaw response:\n{text}")


MM_BRAND_PREAMBLE = """You are part of the Man Matters Statics Builder — a multi-agent pipeline that turns
a reference creative brief into an on-brand static ad for Man Matters Shilajit Gummies.

Brand: Man Matters (Indian men's health D2C)
Product: Shilajit Gummies, 60 ct, ₹899
Tone: Clean, confident, science-backed, modern-masculine
Audience: Indian men, 25–45, urban, health-conscious

Hard rules across the whole pipeline:
- The product jar must never be reimagined. A real product cutout will be composited later.
- All copy is typeset from the provided deck. Never invent claims or change wording.
- Aesthetic is premium and minimal. One hero message per static. Maximum 3 claims.
- Palette is constrained to the brand tokens. No purple, neon, or off-brand colors.
- Typography is sans-serif only.
"""

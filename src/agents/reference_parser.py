"""Agent 1b: Reference Parser.

When a reference static is provided (e.g., a competitor ad or an MM exemplar
whose composition we want to emulate), this agent uses Claude vision to extract
its structural layout — where the product lives, where the headline/subhead/
footer go, what the palette is, and the overall mood.

The output feeds the EditorState builder so the interactive editor starts with
reference-matched positions. User still has full freedom to tweak.
"""
from __future__ import annotations

from pathlib import Path

from ..clients.anthropic_client import call_claude
from ..models import ReferenceLayout
from ._common import parse_model


_SYSTEM = """You analyze advertising static creatives and extract their structural layout. Return JSON only — no prose, no markdown. Your entire response is a single valid JSON object."""


def run(reference_image_path: Path) -> ReferenceLayout:
    user_text = """Analyze this advertising static and extract its structural layout as normalized coordinates (0.0 to 1.0 — fractions of the image width/height).

Return JSON with this exact shape:
{
  "product": {"x": <0-1>, "y": <0-1>, "w": <0-1>, "h": <0-1>} | null,
  "headline": {"x": <0-1>, "y": <0-1>, "w": <0-1>, "h": <0-1>} | null,
  "subhead": {"x": <0-1>, "y": <0-1>, "w": <0-1>, "h": <0-1>} | null,
  "bottom_strip": {"x": <0-1>, "y": <0-1>, "w": <0-1>, "h": <0-1>} | null,
  "logo_position": "top-left" | "top-right" | "bottom-left" | "bottom-right",
  "palette_hex": ["#RRGGBB", ...],
  "mood": "<one sentence describing the overall mood and aesthetic>",
  "notes": "<composition observations useful for replicating the structure>"
}

Rules:
- x,y = top-left corner of each bounding box as a fraction of the image's width/height.
- w,h = width and height as fractions. So x+w and y+h should be ≤ 1.0.
- Product = the primary product shown (bottle, jar, pack, etc.). If no product visible, set null.
- Headline = the largest, boldest text. If no clear headline, set null.
- Subhead = secondary text typically just below or near the headline.
- Bottom strip = a thin row of attributes/claims near the bottom (pipe-separated items, a CTA row, etc.), if present.
- Palette = 3 to 5 dominant brand colors in the composition as hex values.
- Mood = brief description (e.g. "minimal beige editorial" or "dark dramatic premium").
- Notes = anything about hierarchy, whitespace, visual balance, negative space worth noting.

Be precise with coordinates — they'll be used to recompose a new static with the same structure."""

    response = call_claude(
        system=_SYSTEM,
        user_text=user_text,
        image_paths=[reference_image_path],
        temperature=0.0,
        max_tokens=900,
    )
    return parse_model(response, ReferenceLayout)

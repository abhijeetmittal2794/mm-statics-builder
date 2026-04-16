"""Agent 1: Brief Parser.

Reads the raw BuildInput (reference static + product image + copy deck) and emits
a ParsedBrief: structured intent the rest of the pipeline can act on.
"""
from __future__ import annotations

from pathlib import Path

from ..clients.anthropic_client import call_claude
from ..models import BuildInput, ParsedBrief
from ._common import MM_BRAND_PREAMBLE, parse_model


SYSTEM = MM_BRAND_PREAMBLE + """
Your specific role: Brief Parser (the "category person").

You read the inputs and answer:
  1. What is this static TRYING to do? (the claim type)
  2. What is the emotional or rational hook?
  3. What mood/keywords describe the reference aesthetic?
  4. What layout zones does the copy deck imply?
  5. Does this need a human figure in frame?

Return ONLY a JSON object matching this schema (no prose before or after):
{
  "claim_type": "ingredient" | "benefit" | "problem" | "comparison" | "social_proof" | "price" | "testing" | "usage" | "absorption",
  "audience_hook": "<one sentence>",
  "reference_mood_keywords": ["<kw1>", "<kw2>", ...],
  "layout_zones": [{"name": "...", "purpose": "...", "priority": 1}, ...],
  "has_human_figure": true | false,
  "notes": "<any observations that downstream agents should know>"
}
"""


def run(inp: BuildInput) -> ParsedBrief:
    user_text = _build_user_text(inp)
    images: list[Path] = []
    if inp.reference_static_path:
        images.append(Path(inp.reference_static_path))
    images.append(Path(inp.product_image_path))
    for p in inp.prop_image_paths:
        images.append(Path(p))

    response = call_claude(
        system=SYSTEM,
        user_text=user_text,
        image_paths=images,
        temperature=0.3,
    )
    return parse_model(response, ParsedBrief)


def _build_user_text(inp: BuildInput) -> str:
    cd = inp.copy_deck
    lines = [
        f"Target format: {inp.format}",
        f"Tone tag: {cd.tone_tag}",
        "",
        "Copy deck:",
        f"  Headline: {cd.headline}",
    ]
    if cd.subhead:
        lines.append(f"  Subhead: {cd.subhead}")
    if cd.claim_bullets:
        lines.append(f"  Claims: {cd.claim_bullets}")
    if cd.cta:
        lines.append(f"  CTA: {cd.cta}")
    if cd.bottom_strip:
        lines.append(f"  Bottom strip: {cd.bottom_strip}")
    if cd.legal:
        lines.append(f"  Legal: {cd.legal}")
    if inp.template_hint:
        lines.append(f"\nTemplate hint from user: {inp.template_hint}")
    lines.append("\nImages attached: reference static (if any), product, props (if any).")
    return "\n".join(lines)

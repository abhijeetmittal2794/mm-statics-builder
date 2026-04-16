"""Agent 4: Casting Director.

Only runs when the brief needs a human in frame. Produces a CastingSpec that the
Scene Generator will execute against (or routes to a real shot-library for hero shots).

V1 note: Template B (the MVP) doesn't use humans, so this agent is wired up but
not exercised on the default path. It's ready for Templates D, F, J which do.
"""
from __future__ import annotations

from ..clients.anthropic_client import call_claude
from ..models import CastingSpec, ConceptCard, ParsedBrief
from ._common import MM_BRAND_PREAMBLE, parse_model


SYSTEM = MM_BRAND_PREAMBLE + """
Your specific role: Casting Director.

You only act when a human figure is part of the concept. Your job:

  1. Assign a TIER:
     - "hero": face + product in same frame, category is appearance-driven (hair/beard/skin).
       Recommend using a real licensed photo (set use_real_reference_image to a path).
     - "supporting": face visible but not selling a visible result. Generate with controls.
     - "ambient": silhouette, cropped, or back-turned. Generate freely.
     - "none": no human needed.

  2. Specify ethnicity (Indian), age band, wardrobe, pose, expression.
  3. Write a crop strategy — if in doubt, crop out hands to avoid finger errors.
  4. Write skin notes — natural texture, pores at close crops, no plastic/waxy finish.
  5. Provide a negative-prompt list of AI-tells to avoid.

Return ONLY JSON:
{
  "tier": "hero" | "supporting" | "ambient" | "none",
  "ethnicity": "Indian",
  "age_band": "25-40",
  "wardrobe": "...",
  "pose": "...",
  "crop_strategy": "...",
  "skin_notes": "...",
  "negative_prompts": ["...", ...],
  "use_real_reference_image": "<path or null>"
}
"""


def run(brief: ParsedBrief, concept: ConceptCard) -> CastingSpec:
    if not brief.has_human_figure:
        return CastingSpec(tier="none")

    user_text = (
        "=== BRIEF ===\n"
        f"{brief.model_dump_json(indent=2)}\n\n"
        "=== CONCEPT CARD ===\n"
        f"{concept.model_dump_json(indent=2)}\n\n"
        "Emit the CastingSpec JSON."
    )
    response = call_claude(system=SYSTEM, user_text=user_text, temperature=0.4)
    return parse_model(response, CastingSpec)

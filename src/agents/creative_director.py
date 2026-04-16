"""Agent 3: Creative Director.

Adds the "creative layer" — generates 2–3 distinct concepts per brief.
Each concept describes scene + placement + negative-space map that the Scene
Generator and Compositor will execute.
"""
from __future__ import annotations

import json

from ..clients.anthropic_client import call_claude
from ..models import BrandSpec, ConceptCard, ParsedBrief
from ._common import MM_BRAND_PREAMBLE, extract_json


SYSTEM = MM_BRAND_PREAMBLE + """
Your specific role: Creative Director.

You receive a ParsedBrief and a BrandSpec (with chosen template).
You produce 3 distinct concept cards. Each concept must:
  - Describe a SCENE only — never describe the product itself in detail (the product will be composited).
  - Specify product placement (position, tilt, scale) in words the compositor can act on.
  - Specify prop placement if the template uses props.
  - Specify where copy will live (the "negative space map").
  - Specify lighting so the scene matches the product photo's lighting.
  - Pin expected palette hex values.

Tonal range across 3 concepts:
  - Concept 1: most literal / safe execution of the template
  - Concept 2: moderate creative twist — metaphor or visual pun
  - Concept 3: boldest — still on-brand but surprising composition

Never describe: the jar's label text, any copy typography, any human face details (that's Casting Director's job if needed).

Return ONLY a JSON array of 3 concept cards (no prose):
[
  {
    "concept_name": "...",
    "scene_description": "...",
    "metaphor": "... or null",
    "product_placement": "...",
    "prop_placement": "... or null",
    "negative_space_map": "...",
    "lighting_direction": "...",
    "expected_palette_hex": ["#...", ...]
  },
  ...
]
"""


def run(brief: ParsedBrief, brand: BrandSpec) -> list[ConceptCard]:
    user_text = (
        "=== BRIEF ===\n"
        f"{brief.model_dump_json(indent=2)}\n\n"
        "=== BRAND SPEC ===\n"
        f"{brand.model_dump_json(indent=2)}\n\n"
        "Emit 3 concept cards as a JSON array."
    )
    response = call_claude(
        system=SYSTEM,
        user_text=user_text,
        temperature=0.7,  # higher for creative variance
    )
    # Parse array
    text = response
    # tolerate fences
    if "```" in text:
        import re
        m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
        if m:
            text = m.group(1)
    else:
        import re
        m = re.search(r"(\[.*\])", text, re.DOTALL)
        if m:
            text = m.group(1)
    data = json.loads(text)
    return [ConceptCard.model_validate(item) for item in data]

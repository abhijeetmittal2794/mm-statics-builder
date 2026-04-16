"""Agent 2: Brand Translator.

Maps the reference aesthetic to Man Matters' visual language using design.md + exemplars.
Picks the MM template and pins palette/typography.
"""
from __future__ import annotations

from ..brand.pack import list_exemplar_statics, load_design_guide
from ..clients.anthropic_client import call_claude
from ..models import BrandSpec, BuildInput, ParsedBrief
from ._common import MM_BRAND_PREAMBLE, parse_model


SYSTEM = MM_BRAND_PREAMBLE + """
Your specific role: Brand Translator.

You are given:
  - The full Man Matters design guide
  - 10–12 exemplar statics from the current Shilajit campaign
  - The parsed brief for the new static

Your job:
  1. Choose ONE of the 10 templates (A–J) that best fits the brief.
  2. Decide the background mood (warm_beige, cool_light_grey, dark_moody, pure_white, mountain_sky).
  3. Pin the primary palette (3–5 hex values drawn from design.md tokens only).
  4. Write compact typography notes for the downstream typesetter.
  5. Write a one-paragraph composition intent.
  6. List brand guardrails that apply to this static.

Return ONLY a JSON object matching this schema:
{
  "chosen_template": "A"-"J",
  "background_mood": "...",
  "primary_palette_hex": ["#...", ...],
  "typography_notes": "...",
  "composition_intent": "...",
  "brand_guardrails_applied": ["...", ...]
}
"""


def run(inp: BuildInput, brief: ParsedBrief) -> BrandSpec:
    guide = load_design_guide()
    exemplars = list_exemplar_statics(max_count=8)

    user_text = (
        "=== MAN MATTERS DESIGN GUIDE ===\n\n"
        f"{guide}\n\n"
        "=== PARSED BRIEF ===\n"
        f"{brief.model_dump_json(indent=2)}\n\n"
        f"=== USER TEMPLATE HINT (optional) ===\n"
        f"{inp.template_hint or '(none — pick the best fit)'}\n\n"
        "Attached images are exemplar MM statics. Use them as the visual ground truth for "
        "palette, composition, and tone. Then emit the BrandSpec JSON."
    )

    response = call_claude(
        system=SYSTEM,
        user_text=user_text,
        image_paths=exemplars,
        temperature=0.3,
    )
    return parse_model(response, BrandSpec)

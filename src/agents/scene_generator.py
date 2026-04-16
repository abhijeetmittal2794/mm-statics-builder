"""Agent 5: Scene Generator — backdrop only.

Produces a clean surface + lighting atmosphere. Nothing else. No props, no product,
no copy, no humans. The Scene Integrator is responsible for placing objects on top.

This radical narrowing of scope is why the model obeys us now: we're asking it
to do one thing well (atmosphere) instead of three things at once.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from ..brand.pack import list_exemplar_statics
from ..clients.nano_banana import generate_scene
from ..models import (
    BrandSpec,
    BuildInput,
    CastingSpec,
    ConceptCard,
    ParsedBrief,
    SceneArtifact,
)
from ..product.registry import label_references

OUTPUTS_DIR = Path(__file__).resolve().parents[2] / "outputs"


def run(
    *,
    inp: BuildInput,
    brief: ParsedBrief,
    brand: BrandSpec,
    concept: ConceptCard,
    casting: CastingSpec,
) -> SceneArtifact:
    prompt = _build_prompt(brand, concept)
    # Exemplars give palette/tonality cue. Label refs give lighting-warmth cue.
    refs = list_exemplar_statics(max_count=3) + label_references(max_count=1)

    out_path = OUTPUTS_DIR / "scenes" / f"scene_{uuid.uuid4().hex[:10]}.png"
    generate_scene(
        prompt=prompt,
        reference_images=refs,
        out_path=out_path,
        aspect_ratio=inp.format,
    )
    return SceneArtifact(
        scene_image_path=str(out_path),
        placeholder_mask_path=None,
        prompt_used=prompt,
    )


def _build_prompt(brand: BrandSpec, concept: ConceptCard) -> str:
    palette = ", ".join(concept.expected_palette_hex or brand.primary_palette_hex)
    mood = brand.background_mood.replace("_", " ")
    return f"""Produce a clean product-photography BACKDROP only. This is a surface for objects to be placed on top of — not a finished composition.

ABSOLUTE RULES — violation is disqualifying:
- DO NOT render any product, jar, bottle, package, container, or consumable.
- DO NOT render any ingredient, prop, bowl, or still-life object.
- DO NOT render any text, letters, numbers, words, logos, or typographic elements.
- DO NOT render any human, hand, silhouette, or figure.
- DO NOT render any object. Backdrop and lighting only.

WHAT TO RENDER:
- A clean continuous surface with gentle organic texture (paper, linen, matte concrete, or similar — appropriate to the mood).
- Soft, professional studio lighting from the upper-right, ~4500K white balance, subtle falloff.
- Slight warm vignette if warm mood, subtle cool gradient if cool mood.
- A believable shallow depth of field — the foreground area should read as an inviting "stage" for objects.
- Space and composition should suggest where an object could sit naturally in the lower-left third.

MOOD: {mood}
PALETTE (strict): {palette}
LIGHTING NOTE FROM CONCEPT: {concept.lighting_direction}

STYLE:
Editorial, minimal, premium. Indian D2C wellness brand tone. The attached images are the current Man Matters visual language — match their surface warmth, lighting softness, and overall cleanliness. Do NOT copy their composition.

FORMAT: high resolution, sharp focus, no motion blur, no grain, no vignetting effects beyond subtle natural falloff.

Remember: this is ONLY a backdrop. A later step will place the product and ingredient props on it. Any object, text, or figure in your output is a failure.
"""

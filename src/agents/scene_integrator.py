"""Agent 5b: Scene Integrator.

Produces a harmonized backdrop + jar composite. The integrator's job is SHADOW and
LIGHTING integration — making the jar look like it was photographed on the backdrop.

Label fidelity is NOT this agent's job. The downstream Product Restamp step
overwrites the jar pixels with the original cutout, so any label drift here is
automatically corrected. That frees the integrator to focus fully on realism.

No ingredient props are passed. Props are a V2 feature for templates that use them.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from PIL import Image

from ..clients.nano_banana import edit_image
from ..models import (
    BrandSpec,
    CastingSpec,
    ConceptCard,
    IntegrationArtifact,
    ParsedBrief,
)
from ..product.prep import prepare_cutout
from ..product.registry import hero_silhouette

OUTPUTS_DIR = Path(__file__).resolve().parents[2] / "outputs"


def run(
    *,
    scene_path: Path,
    brief: ParsedBrief,
    brand: BrandSpec,
    concept: ConceptCard,
    casting: CastingSpec | None = None,
    aspect_ratio: str = "4:5",
) -> IntegrationArtifact:
    product_cutout = prepare_cutout(hero_silhouette())
    input_images = [scene_path, product_cutout]
    prompt = _build_prompt(concept, brand, casting)

    out_path = OUTPUTS_DIR / "integrated" / f"integrated_{uuid.uuid4().hex[:10]}.png"
    edit_image(
        prompt=prompt,
        input_images=input_images,
        out_path=out_path,
        aspect_ratio=aspect_ratio,
    )

    # Nominal product bbox matches the prompted position — used as the fallback
    # target if the restamp's vision-based bbox detection fails.
    w, h = Image.open(out_path).size
    cx, cy = int(w * 0.55), int(h * 0.55)
    pw, ph = int(w * 0.40), int(h * 0.55)
    nominal_bbox = (cx - pw // 2, cy - ph // 2, cx + pw // 2, cy + ph // 2)

    return IntegrationArtifact(
        integrated_image_path=str(out_path),
        product_bbox_xyxy=nominal_bbox,
        prop_bboxes=[],
        prompt_used=prompt,
        drift_score=None,  # No longer measured — restamp replaces pixels directly.
        passed_integrity_check=True,
        used_fallback=False,
    )


def _build_prompt(concept: ConceptCard, brand: BrandSpec, casting: CastingSpec | None = None) -> str:
    palette = ", ".join(concept.expected_palette_hex or brand.primary_palette_hex)
    human_block = _human_block(casting)
    return f"""You are placing a photographed product into a backdrop. This is a photography compositing and relighting task — not an imagination task.

INPUTS:
- Image 1: the backdrop scene.
- Image 2: the product — a Man Matters Shilajit Gummies jar on transparent background. This is the exact product; treat image 2 as a photograph reference.

PRODUCT POSITION (strict):
- Exactly ONE jar in the final image. Singular. A single solitary product.
- Placement: center-right of the canvas. The jar's horizontal center is at ~55% of canvas width. The jar's vertical center is at ~55% of canvas height.
- Size: the jar occupies approximately 40% of canvas width and 55% of canvas height.
- Orientation: UPRIGHT, facing the camera, in the EXACT orientation shown in image 2. DO NOT rotate, tilt, flip, or turn the jar.

SINGULARITY RULES — violation is disqualifying:
- Render EXACTLY ONE jar. Not two. Not a pair. Not a hero plus a background unit.
- DO NOT duplicate the jar, mirror it, show another one behind it, or arrange multiple product units in depth.
- DO NOT include any secondary jar, faded jar, out-of-focus jar, or second instance of the product in the background.
- The final image contains one jar and one jar only.

EMPTY ZONES (leave clear of any object):
- Upper third of canvas — reserved for typography (added later in code).
- Lower eighth of canvas — reserved for a footer strip.

YOUR PRIMARY JOB — scene integration:
- Cast a soft realistic contact shadow directly under the base of the jar where it meets the surface. The shadow is short, soft-edged, and grounded. The jar must read as STANDING ON the surface, not floating.
- Subtle ambient occlusion at the jar's base, feathering into the surface.
- Match the jar's lighting to the backdrop's key light (soft, from upper-right, ~4500K white balance). The jar's own highlights and shadows should read as if it were photographed in this scene.
- Very subtle atmospheric color cohesion so the jar and backdrop share the same scene temperature.
- The jar and its shadow should feel like a single photograph, not a cutout placed on a background.

{human_block}

HARD RULES — violation is disqualifying:
- DO NOT render any text, numbers, letters, words, or logos anywhere in the output EXCEPT what already exists on image 2's product label.
- DO NOT add any additional objects, props, ingredients, bowls, dishes, or decorations beyond what is specified above.
- DO NOT rotate, tilt, flip, or rescale the jar beyond what is shown in image 2.

PALETTE: {palette}

OUTPUT: a single premium editorial composite — the jar on the backdrop with realistic grounded shadow and cohesive lighting. Clean, minimal.
"""


def _human_block(casting: CastingSpec | None) -> str:
    if not casting or casting.tier in (None, "none"):
        return "HUMAN FIGURE: none in this composition. DO NOT add any human, hand, or figure."
    bits = [
        f"HUMAN FIGURE (include in scene — tier: {casting.tier}):",
        f"- Ethnicity: {casting.ethnicity}; age band: {casting.age_band}",
        f"- Wardrobe: {casting.wardrobe}",
        f"- Pose: {casting.pose}",
        f"- Crop strategy: {casting.crop_strategy}",
        f"- Skin: {casting.skin_notes}",
        "- The human must look natural, authentic — not stock-photo or AI-plastic.",
        "- Natural skin texture with pores, slight asymmetry, realistic hair.",
    ]
    if casting.negative_prompts:
        bits.append("- AVOID: " + "; ".join(casting.negative_prompts))
    return "\n".join(bits)

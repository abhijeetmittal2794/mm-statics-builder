"""Agent 6: Compositor & Typesetter.

Three possible paths:
  A. Design Pass succeeded + typography verified → save the designed image as
     final. No code typography needed.
  B. Design Pass failed OR typography verification failed → code typesets on
     top of the restamped image (existing Template-B typography logic).
  C. Restamp unavailable (integrator upstream failed) → code typesets on top
     of a full alpha composite onto the raw backdrop.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from PIL import Image

from ..brand.tokens import CANVAS_SIZES
from ..layouts import template_b
from ..models import (
    BrandSpec,
    BuildInput,
    CompositedStatic,
    DesignedArtifact,
    ParsedBrief,
    RestampArtifact,
    SceneArtifact,
)
from ..product.prep import prepare_cutout
from ..product.registry import hero_silhouette

OUTPUTS_DIR = Path(__file__).resolve().parents[2] / "outputs"


def run(
    *,
    inp: BuildInput,
    brief: ParsedBrief,
    brand: BrandSpec,
    scene: SceneArtifact,
    restamp: RestampArtifact | None,
    designed: DesignedArtifact | None,
) -> CompositedStatic:
    canvas_size = CANVAS_SIZES[inp.format]
    out_path = OUTPUTS_DIR / "statics" / f"static_{uuid.uuid4().hex[:10]}.png"

    # Path A: Design Pass produced an image — use it directly.
    # The NBP-designed look is consistently better than code typography
    # even with occasional minor letter imperfections. Code typography
    # only kicks in as a crash fallback (Path B/C below).
    if designed and designed.designed_image_path:
        return _copy_designed_as_final(
            designed_path=Path(designed.designed_image_path),
            canvas_size=canvas_size,
            out_path=out_path,
            restamp_bbox=restamp.detected_bbox if restamp else (0, 0, 0, 0),
        )

    ingredient_name = _ingredient_name_for(brief)

    # Path B: restamp worked; code typesets on top
    if restamp:
        return template_b.render_on_integrated(
            integrated_path=Path(restamp.restamped_image_path),
            copy=inp.copy_deck,
            brand=brand,
            canvas_size=canvas_size,
            output_path=out_path,
            show_ingredient_name=ingredient_name,
            product_bbox=restamp.detected_bbox,
        )

    # Path C: restamp missing; full alpha composite onto raw backdrop
    product_cutout = prepare_cutout(hero_silhouette())
    return template_b.render_alpha_composite(
        scene_path=Path(scene.scene_image_path),
        product_cutout_path=product_cutout,
        prop_cutout_path=None,
        copy=inp.copy_deck,
        brand=brand,
        canvas_size=canvas_size,
        output_path=out_path,
        show_ingredient_name=ingredient_name,
    )


def _copy_designed_as_final(
    *,
    designed_path: Path,
    canvas_size: tuple[int, int],
    out_path: Path,
    restamp_bbox: tuple[int, int, int, int],
) -> CompositedStatic:
    """NBP's designed image becomes the final. Resize to canonical canvas dimensions."""
    img = Image.open(designed_path).convert("RGB").resize(canvas_size, Image.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    return CompositedStatic(
        output_path=str(out_path),
        width=canvas_size[0],
        height=canvas_size[1],
        template_used="B",
        product_bbox_xyxy=restamp_bbox,
    )


def _ingredient_name_for(brief: ParsedBrief) -> str | None:
    """Only surface the oversized ingredient display name for ingredient-type briefs."""
    if brief.claim_type != "ingredient":
        return None
    known = ["shilajit", "ashwagandha", "black musli", "chicory root"]
    hay = " ".join([brief.audience_hook] + brief.reference_mood_keywords).lower()
    for k in known:
        if k in hay:
            return k.upper()
    return None

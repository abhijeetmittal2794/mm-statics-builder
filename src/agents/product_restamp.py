"""Agent 5c: Product Restamp.

The integrator places the jar beautifully into the scene with grounded shadows and
matched lighting — but it sometimes warps the label text in the process. This step
detects the jar's location in the integrated image and alpha-composites the ORIGINAL
product cutout on top. The integrator's shadow and lighting integration are preserved
because they lie outside the cutout's alpha silhouette. Only the jar pixels are
replaced, guaranteeing pixel-perfect label fidelity.

Detection strategy (three-tier, most reliable first):
  1. Diff-based: compare backdrop to integrated image pixel-wise. The jar body is
     a dark, tightly-bounded region that changed significantly — unambiguous to find
     with numpy. Deterministic, free, always works when the integrator did anything.
  2. Vision LLM: Claude vision call returning tight bbox JSON. Used if diff detection
     produces a nonsensical result.
  3. Hardcoded: matches the integrator's prompted position. Last-resort only.
"""
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from ..clients.anthropic_client import call_claude
from ..models import RestampArtifact

OUTPUTS_DIR = Path(__file__).resolve().parents[2] / "outputs"

# Padding around the detected bbox. Covers any slight detection miss so the
# stamped cutout fully occludes the integrator's jar pixels.
BBOX_PADDING_RATIO = 0.04

# Sanity bounds for any detection method — reject obvious nonsense.
MIN_AREA_RATIO = 0.08
MAX_AREA_RATIO = 0.85


def run(
    *,
    scene_path: Path,
    integrated_path: Path,
    product_cutout_path: Path,
    fallback_bbox: tuple[int, int, int, int],
) -> RestampArtifact:
    detection_method = "diff"
    try:
        bbox = _detect_jar_bbox_via_diff(scene_path, integrated_path)
    except Exception:
        try:
            bbox = _detect_jar_bbox_via_vision(integrated_path)
            detection_method = "vision_llm"
        except Exception:
            bbox = fallback_bbox
            detection_method = "hardcoded_fallback"

    out_path = OUTPUTS_DIR / "restamped" / f"restamped_{uuid.uuid4().hex[:10]}.png"
    _stamp(integrated_path, product_cutout_path, bbox, out_path)

    return RestampArtifact(
        restamped_image_path=str(out_path),
        detected_bbox=bbox,
        detection_method=detection_method,  # type: ignore
    )


# ---------- Primary detection: pixel diff between backdrop and integrated ----------

def _detect_jar_bbox_via_diff(
    scene_path: Path,
    integrated_path: Path,
) -> tuple[int, int, int, int]:
    """Find the jar via pixel difference.

    The jar body is much darker than any MM backdrop and is the dominant visual
    change the integrator introduced. We separate it from the shadow (which also
    shows up in the diff but is much softer) by requiring (a) significant RGB
    change AND (b) the pixel ends up very dark in the integrated image.

    We then take the tight bounding box of that region and extend it slightly
    upward to include the white cap (which is lighter and might not meet the
    'dark' criterion on its own).
    """
    integrated_img = Image.open(integrated_path).convert("RGB")
    W, H = integrated_img.size

    backdrop_img = Image.open(scene_path).convert("RGB").resize((W, H), Image.LANCZOS)

    integrated = np.asarray(integrated_img, dtype=np.int16)
    backdrop = np.asarray(backdrop_img, dtype=np.int16)

    # RGB channel-summed change, 0..765
    delta = np.abs(integrated - backdrop).sum(axis=2)
    changed = delta > 45  # anything meaningfully different from backdrop

    # Luminance of the integrated image; jar body is < ~50 on 0..255 scale.
    lum = integrated.mean(axis=2)
    dark = lum < 70

    # Jar body = changed AND dark. Shadows are changed but much brighter than this.
    jar_body = changed & dark
    if jar_body.sum() < (W * H) * 0.02:
        raise ValueError("diff found too little dark-change area to be a jar body")

    # Tight bbox of the dark body
    rows = np.any(jar_body, axis=1)
    cols = np.any(jar_body, axis=0)
    y_body_top = int(np.argmax(rows))
    y_body_bot = H - int(np.argmax(rows[::-1])) - 1
    x_left = int(np.argmax(cols))
    x_right = W - int(np.argmax(cols[::-1])) - 1

    # Extend upward ~18% of body height to capture the white cap (which is
    # light and won't register as "dark"). Cap is 15–20% of total jar height.
    body_h = y_body_bot - y_body_top
    cap_extension = int(body_h * 0.22)
    y_top = max(0, y_body_top - cap_extension)

    bbox = (x_left, y_top, x_right, y_body_bot)
    _validate_bbox(bbox, W, H)
    return bbox


# ---------- Secondary: Claude vision ----------

_BBOX_SYSTEM = (
    "You are a precise object detector. Respond with JSON only — no prose, no markdown, "
    "no code fences. Your entire response must be a single valid JSON object."
)


def _detect_jar_bbox_via_vision(integrated_path: Path) -> tuple[int, int, int, int]:
    img = Image.open(integrated_path)
    w, h = img.size

    user_text = (
        f"Image dimensions: {w} px wide by {h} px tall.\n\n"
        "Return the TIGHT bounding box of the product jar (the cylindrical bottle/container "
        "with a white cap and black body) in this image.\n\n"
        "IMPORTANT: exclude any cast shadow, reflection, or the surface the jar sits on. "
        "Include ONLY the solid body of the jar itself, from the very top of the white cap "
        "to the bottom of the jar's base where it meets the surface.\n\n"
        "Coordinate system: pixels from top-left corner. x grows right, y grows down. "
        "x1 > x0, y1 > y0, all values within [0, image_dimension].\n\n"
        'Respond with exactly this JSON shape:\n'
        '{"x0": <int>, "y0": <int>, "x1": <int>, "y1": <int>}'
    )

    response = call_claude(
        system=_BBOX_SYSTEM,
        user_text=user_text,
        image_paths=[integrated_path],
        temperature=0.0,
        max_tokens=200,
    )

    match = re.search(r'\{[^}]*"x0"[^}]*\}', response, re.DOTALL)
    if not match:
        raise ValueError(f"no bbox JSON in response: {response[:200]}")
    data = json.loads(match.group(0))
    bbox = (int(data["x0"]), int(data["y0"]), int(data["x1"]), int(data["y1"]))
    _validate_bbox(bbox, w, h)
    return bbox


# ---------- Shared validation ----------

def _validate_bbox(bbox: tuple[int, int, int, int], w: int, h: int) -> None:
    x0, y0, x1, y1 = bbox
    if not (0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h):
        raise ValueError(f"bbox out of canvas: {bbox} for {w}x{h}")
    area_ratio = ((x1 - x0) * (y1 - y0)) / (w * h)
    if not (MIN_AREA_RATIO <= area_ratio <= MAX_AREA_RATIO):
        raise ValueError(f"bbox area ratio {area_ratio:.2f} outside [{MIN_AREA_RATIO}, {MAX_AREA_RATIO}]")


# ---------- Stamping ----------

def _stamp(
    integrated_path: Path,
    cutout_path: Path,
    bbox: tuple[int, int, int, int],
    out_path: Path,
) -> None:
    base = Image.open(integrated_path).convert("RGBA")
    cutout = Image.open(cutout_path).convert("RGBA")

    x0, y0, x1, y1 = bbox
    bbox_w = x1 - x0
    bbox_h = y1 - y0

    pad_w = int(bbox_w * BBOX_PADDING_RATIO)
    pad_h = int(bbox_h * BBOX_PADDING_RATIO)
    target_w = bbox_w + 2 * pad_w
    target_h = bbox_h + 2 * pad_h

    cutout_aspect = cutout.width / cutout.height
    target_aspect = target_w / target_h

    if cutout_aspect > target_aspect:
        new_w = target_w
        new_h = int(new_w / cutout_aspect)
    else:
        new_h = target_h
        new_w = int(new_h * cutout_aspect)

    cutout_resized = cutout.resize((new_w, new_h), Image.LANCZOS)

    # Edge cleanup: erode the alpha by 2px (MinFilter size=5) to strip any
    # residual halo from rembg's original white-background cut, then
    # gaussian-blur 2.5px to feather the new edge naturally. Kills the faint
    # rectangular outline around the jar.
    alpha = cutout_resized.split()[-1]
    alpha_eroded = alpha.filter(ImageFilter.MinFilter(size=5))
    alpha_feathered = alpha_eroded.filter(ImageFilter.GaussianBlur(radius=2.5))
    cutout_resized.putalpha(alpha_feathered)

    # Bottom-align within the padded bbox so the base meets the contact shadow
    paste_x = x0 - pad_w + (target_w - new_w) // 2
    paste_y = y1 + pad_h - new_h

    base.alpha_composite(cutout_resized, (paste_x, paste_y))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out_path, "PNG", optimize=True)

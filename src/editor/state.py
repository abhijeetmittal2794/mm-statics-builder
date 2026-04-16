"""Editor state model + helper to build the default layout from a pipeline run.

The editor always renders from scratch — backdrop + product cutout + text layers —
so the user has full control over position and size of every element. The
NBP-designed image is NOT used as a base because its text and product are baked in.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from ..brand.tokens import CANVAS_SIZES
from ..models import PipelineRun
from ..product.prep import prepare_cutout
from ..product.registry import hero_silhouette

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAYOUTS_DIR = PROJECT_ROOT / "outputs" / "layouts"


class TextElement(BaseModel):
    id: str
    content: str
    x: int
    y: int
    width: int
    size: int
    font_role: Literal["headline_bold", "body", "body_bold", "label_caps"]
    color: str
    align: Literal["left", "center", "right"] = "left"
    line_spacing: float = 1.1


class ProductElement(BaseModel):
    cutout_path: str
    x: int
    y: int
    width: int
    height: int
    rotation: int = 0


class EditorState(BaseModel):
    run_id: str
    canvas_width: int
    canvas_height: int
    backdrop_path: str
    product: ProductElement
    texts: list[TextElement] = Field(default_factory=list)
    logo_on_dark: bool = False
    logo_width_ratio: float = 0.13
    bottom_rule: bool = True


# ---------- Default layout from a pipeline run ----------

def build_default_layout(pr: PipelineRun) -> EditorState:
    canvas_w, canvas_h = CANVAS_SIZES[pr.input.format]
    margin = int(canvas_w * 0.05)
    ref = pr.reference_layout  # optional — when set, overrides default positions

    backdrop_path = pr.scene.scene_image_path if pr.scene else ""

    product_cutout = prepare_cutout(hero_silhouette())
    if ref and ref.product:
        x0, y0, x1, y1 = ref.product.to_pixels(canvas_w, canvas_h)
        product = ProductElement(
            cutout_path=str(product_cutout),
            x=x0, y=y0, width=x1 - x0, height=y1 - y0,
        )
    elif pr.restamp:
        x0, y0, x1, y1 = pr.restamp.detected_bbox
        product = ProductElement(
            cutout_path=str(product_cutout),
            x=x0, y=y0,
            width=x1 - x0,
            height=y1 - y0,
        )
    else:
        pw = int(canvas_w * 0.40)
        ph = int(canvas_h * 0.50)
        product = ProductElement(
            cutout_path=str(product_cutout),
            x=int(canvas_w * 0.35), y=int(canvas_h * 0.33),
            width=pw, height=ph,
        )

    on_dark = pr.brand and pr.brand.background_mood == "dark_moody"
    primary_color = "#FFFFFF" if on_dark else "#1C1C1C"
    secondary_color = "#DDDDDD" if on_dark else "#5A5A5A"

    copy = pr.input.copy_deck
    texts: list[TextElement] = []

    # Headline
    if ref and ref.headline:
        x0, y0, x1, y1 = ref.headline.to_pixels(canvas_w, canvas_h)
        size = max(18, int((y1 - y0) * 0.55))
        texts.append(TextElement(
            id="headline", content=copy.headline,
            x=x0, y=y0, width=x1 - x0,
            size=size, font_role="headline_bold",
            color=primary_color, align="left",
        ))
    else:
        texts.append(TextElement(
            id="headline", content=copy.headline,
            x=margin, y=int(canvas_h * 0.11),
            width=canvas_w - 2 * margin,
            size=int(78 * canvas_w / 1080),
            font_role="headline_bold", color=primary_color, align="left",
        ))

    # Subhead
    if copy.subhead:
        if ref and ref.subhead:
            x0, y0, x1, y1 = ref.subhead.to_pixels(canvas_w, canvas_h)
            size = max(14, int((y1 - y0) * 0.45))
            texts.append(TextElement(
                id="subhead", content=copy.subhead,
                x=x0, y=y0, width=x1 - x0,
                size=size, font_role="body",
                color=secondary_color, align="left",
            ))
        else:
            texts.append(TextElement(
                id="subhead", content=copy.subhead,
                x=margin, y=int(canvas_h * 0.26),
                width=int(canvas_w * 0.55),
                size=int(30 * canvas_w / 1080),
                font_role="body", color=secondary_color, align="left",
            ))

    # Bottom strip
    if copy.bottom_strip:
        if ref and ref.bottom_strip:
            x0, y0, x1, y1 = ref.bottom_strip.to_pixels(canvas_w, canvas_h)
            size = max(14, int((y1 - y0) * 0.60))
            texts.append(TextElement(
                id="bottom_strip",
                content="  |  ".join(copy.bottom_strip[:3]),
                x=x0, y=y0, width=x1 - x0,
                size=size, font_role="body_bold",
                color=primary_color, align="center",
            ))
        else:
            texts.append(TextElement(
                id="bottom_strip",
                content="  |  ".join(copy.bottom_strip[:3]),
                x=margin, y=int(canvas_h * 0.93),
                width=canvas_w - 2 * margin,
                size=int(24 * canvas_w / 1080),
                font_role="body_bold", color=primary_color, align="center",
            ))

    return EditorState(
        run_id=pr.run_id,
        canvas_width=canvas_w,
        canvas_height=canvas_h,
        backdrop_path=backdrop_path,
        product=product,
        texts=texts,
        logo_on_dark=bool(on_dark),
        logo_width_ratio=0.13,
        bottom_rule=not on_dark,
    )


def save_layout(state: EditorState) -> Path:
    LAYOUTS_DIR.mkdir(parents=True, exist_ok=True)
    out = LAYOUTS_DIR / f"{state.run_id}.json"
    out.write_text(state.model_dump_json(indent=2))
    return out


def load_layout(run_id: str) -> EditorState:
    path = LAYOUTS_DIR / f"{run_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"No layout saved for run_id {run_id}")
    return EditorState.model_validate(json.loads(path.read_text()))

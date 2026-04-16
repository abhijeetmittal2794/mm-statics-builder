"""Renders an EditorState into a final PNG.

This is code-path typography (like the original Compositor), but with every
position, size, and content fully driven by the EditorState JSON — which the
user has interactively adjusted in the browser editor.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..brand.pack import resolve_font
from ..brand.tokens import FONT_ROLES
from ..layouts.logo import draw_wordmark
from .state import EditorState

OUTPUTS_DIR = Path(__file__).resolve().parents[2] / "outputs"


def render(state: EditorState) -> Path:
    canvas = Image.open(state.backdrop_path).convert("RGBA").resize(
        (state.canvas_width, state.canvas_height), Image.LANCZOS
    )

    _paste_product(canvas, state)

    for t in state.texts:
        _draw_text_box(canvas, t)

    if state.bottom_rule:
        _draw_separator_rule(canvas, state)

    draw_wordmark(
        canvas,
        position="top-left",
        on_dark=state.logo_on_dark,
        width_ratio=state.logo_width_ratio,
    )

    out_path = OUTPUTS_DIR / "statics" / f"edited_{state.run_id}_{uuid.uuid4().hex[:6]}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out_path, "PNG", optimize=True)
    return out_path


def _paste_product(canvas: Image.Image, state: EditorState) -> None:
    p = state.product
    product = Image.open(p.cutout_path).convert("RGBA")
    product = product.resize((max(1, p.width), max(1, p.height)), Image.LANCZOS)
    if p.rotation:
        product = product.rotate(p.rotation, resample=Image.BICUBIC, expand=True)

    # Edge cleanup — erode then feather to remove rembg's white-halo fringe.
    alpha = product.split()[-1]
    alpha = alpha.filter(ImageFilter.MinFilter(size=5))
    alpha = alpha.filter(ImageFilter.GaussianBlur(radius=2.5))
    product.putalpha(alpha)

    shadow = _drop_shadow(product, blur=24, opacity=80)
    canvas.alpha_composite(shadow, (p.x - 6, p.y + 12))
    canvas.alpha_composite(product, (p.x, p.y))


def _draw_text_box(canvas: Image.Image, t) -> None:
    font_path = resolve_font(FONT_ROLES[t.font_role])
    if font_path is None:
        font = ImageFont.load_default()
    else:
        font = ImageFont.truetype(str(font_path), size=max(8, t.size))

    lines = _wrap(t.content, font, t.width)
    line_height = int(t.size * t.line_spacing)
    draw = ImageDraw.Draw(canvas)
    y = t.y
    for line in lines:
        bbox = font.getbbox(line)
        line_w = bbox[2] - bbox[0]
        if t.align == "center":
            x = t.x + (t.width - line_w) // 2
        elif t.align == "right":
            x = t.x + t.width - line_w
        else:
            x = t.x
        draw.text((x, y), line, font=font, fill=t.color)
        y += line_height


def _draw_separator_rule(canvas: Image.Image, state: EditorState) -> None:
    # Only draw if there's a bottom_strip text below it
    strip = next((t for t in state.texts if t.id == "bottom_strip"), None)
    if not strip:
        return
    rule_y = strip.y - int(state.canvas_height * 0.01)
    draw = ImageDraw.Draw(canvas, "RGBA")
    margin = int(state.canvas_width * 0.06)
    color = (255, 255, 255, 60) if state.logo_on_dark else (0, 0, 0, 40)
    draw.line(
        [(margin, rule_y), (state.canvas_width - margin, rule_y)],
        fill=color,
        width=2,
    )


def _wrap(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for w in words:
        trial = f"{current} {w}".strip()
        if font.getbbox(trial)[2] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines or [""]


def _drop_shadow(src: Image.Image, *, blur: int, opacity: int) -> Image.Image:
    alpha = src.split()[-1]
    layer = Image.new("RGBA", src.size, (0, 0, 0, 0))
    solid = Image.new("RGBA", src.size, (0, 0, 0, opacity))
    layer.paste(solid, (0, 0), alpha)
    return layer.filter(ImageFilter.GaussianBlur(blur))

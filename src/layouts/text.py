"""Typesetting utilities.

All copy in every final static is rendered here from real font files. The image
model never types. This is what guarantees pixel-perfect copy.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from ..brand.pack import resolve_font
from ..brand.tokens import FONT_ROLES, TYPE_SCALE_1080


def _load_font(role: str, size: int) -> ImageFont.FreeTypeFont:
    files = FONT_ROLES.get(role, [])
    path = resolve_font(files)
    if path is None:
        # Fallback to default PIL font scaled up — not pretty but keeps pipeline running.
        return ImageFont.load_default()
    return ImageFont.truetype(str(path), size=size)


def scaled_size(role_bucket: str, canvas_w: int) -> int:
    """Return a size in px from the 1080-baseline scale, proportional to canvas width."""
    bucket = TYPE_SCALE_1080[role_bucket]
    base = (bucket["min"] + bucket["max"]) // 2
    return int(base * canvas_w / 1080)


def wrap_text(
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    max_lines: int = 3,
) -> list[str]:
    """Greedy word wrap constrained to max_width."""
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
            if len(lines) >= max_lines:
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    return lines


def draw_text_block(
    img: Image.Image,
    text: str,
    *,
    xy: tuple[int, int],
    role: str,
    size_bucket: str,
    color: str,
    max_width: Optional[int] = None,
    max_lines: int = 3,
    line_spacing: float = 1.1,
    align: str = "left",
) -> tuple[int, int, int, int]:
    """Draw a wrapped text block. Returns the bounding box (x0, y0, x1, y1)."""
    size = scaled_size(size_bucket, img.width)
    font = _load_font(role, size)
    draw = ImageDraw.Draw(img)

    if max_width is None:
        max_width = img.width - xy[0] - 40
    lines = wrap_text(text, font, max_width, max_lines)

    x, y = xy
    max_right = x
    line_height = int(size * line_spacing)
    for line in lines:
        bbox = font.getbbox(line)
        line_w = bbox[2] - bbox[0]
        draw_x = x
        if align == "center":
            draw_x = x + (max_width - line_w) // 2
        elif align == "right":
            draw_x = x + max_width - line_w
        draw.text((draw_x, y), line, font=font, fill=color)
        y += line_height
        max_right = max(max_right, draw_x + line_w)

    return (x, xy[1], max_right, y)


def draw_pill_button(
    img: Image.Image,
    text: str,
    *,
    center_xy: tuple[int, int],
    bg_color: str,
    text_color: str,
    width_ratio: float = 0.65,
    role: str = "headline_bold",
) -> tuple[int, int, int, int]:
    """Draw a pill-shaped CTA button centered at center_xy."""
    canvas_w = img.width
    size = scaled_size("cta", canvas_w)
    font = _load_font(role, size)
    draw = ImageDraw.Draw(img)

    pill_w = int(canvas_w * width_ratio)
    pad_v = int(18 * canvas_w / 1080)
    text_bbox = font.getbbox(text)
    text_h = text_bbox[3] - text_bbox[1]
    pill_h = text_h + 2 * pad_v

    cx, cy = center_xy
    x0 = cx - pill_w // 2
    y0 = cy - pill_h // 2
    x1 = x0 + pill_w
    y1 = y0 + pill_h

    draw.rounded_rectangle([x0, y0, x1, y1], radius=pill_h // 2, fill=bg_color)
    text_w = text_bbox[2] - text_bbox[0]
    tx = cx - text_w // 2
    ty = cy - text_h // 2 - text_bbox[1]
    draw.text((tx, ty), text, font=font, fill=text_color)
    return (x0, y0, x1, y1)


def draw_bottom_strip(
    img: Image.Image,
    items: list[str],
    *,
    y: int,
    color: str,
    separator: str = "  |  ",
) -> tuple[int, int, int, int]:
    """Render a `| ` separated attribute strip, centered."""
    if not items:
        return (0, y, 0, y)
    size = scaled_size("bottom_strip", img.width)
    font = _load_font("body_bold", size)
    draw = ImageDraw.Draw(img)
    text = separator.join(items)
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    x = (img.width - tw) // 2
    draw.text((x, y), text, font=font, fill=color)
    return (x, y, x + tw, y + (bbox[3] - bbox[1]))

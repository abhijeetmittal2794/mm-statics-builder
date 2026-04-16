"""Layout for Template B — Ingredient Close-Up (Hero Ingredient).

TWO ENTRY POINTS:

  render_on_integrated(integrated_path, ...)
      When the Scene Integrator produced a harmonized backdrop+product+prop image.
      We only typeset copy on top — product and props are already placed.

  render_alpha_composite(scene_path, ...)
      Fallback when integration failed the drift check. We alpha-composite the
      product cutout and prop photo onto the backdrop ourselves, then typeset.

Vertical zone map (fractions of height, 4:5):
  0.00–0.05  top margin
  0.05–0.12  logo (top-left)
  0.12–0.28  headline block
  0.28–0.33  subhead
  0.33–0.82  product + prop zone
  0.82–0.89  breathing room
  0.89       separator rule (light bg only)
  0.90–0.97  bottom attribute strip
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..brand.pack import resolve_font
from ..brand.tokens import COLORS, FONT_ROLES
from ..models import BrandSpec, CompositedStatic, CopyDeck
from .logo import draw_wordmark
from .text import draw_bottom_strip, draw_text_block, scaled_size


# ---------- Public entry points ----------

def render_on_integrated(
    *,
    integrated_path: Path,
    copy: CopyDeck,
    brand: BrandSpec,
    canvas_size: tuple[int, int],
    output_path: Path,
    show_ingredient_name: str | None = None,
    product_bbox: tuple[int, int, int, int] | None = None,
) -> CompositedStatic:
    """Typeset copy on top of a fully-integrated backdrop+product+prop image."""
    canvas_w, canvas_h = canvas_size
    base = Image.open(integrated_path).convert("RGBA").resize(canvas_size, Image.LANCZOS)
    canvas = base.copy()

    _typeset_common(canvas, copy, brand, show_ingredient_name, product_bbox)
    _save(canvas, output_path)

    return CompositedStatic(
        output_path=str(output_path),
        width=canvas_w,
        height=canvas_h,
        template_used="B",
        product_bbox_xyxy=product_bbox or (0, 0, 0, 0),
    )


def render_alpha_composite(
    *,
    scene_path: Path,
    product_cutout_path: Path,
    prop_cutout_path: Path | None,
    copy: CopyDeck,
    brand: BrandSpec,
    canvas_size: tuple[int, int],
    output_path: Path,
    show_ingredient_name: str | None = None,
) -> CompositedStatic:
    """Fallback path: alpha-composite product + prop onto scene, then typeset."""
    canvas_w, canvas_h = canvas_size
    scene = Image.open(scene_path).convert("RGBA").resize(canvas_size, Image.LANCZOS)
    canvas = scene.copy()

    # --- Product ---
    product_zone_top = int(canvas_h * 0.33)
    product_zone_bottom = int(canvas_h * 0.82)
    product_zone_h = product_zone_bottom - product_zone_top

    product = Image.open(product_cutout_path).convert("RGBA")
    product_target_h = int(product_zone_h * 0.98)
    scale = product_target_h / product.height
    product_w = int(product.width * scale)
    product = product.resize((product_w, product_target_h), Image.LANCZOS)
    product_tilted = product.rotate(-6, resample=Image.BICUBIC, expand=True)

    product_x = int(canvas_w * 0.10)
    product_y = product_zone_bottom - product_tilted.height

    shadow = _make_drop_shadow(product_tilted, blur=28, opacity=85)
    canvas.alpha_composite(shadow, (product_x - 8, product_y + 14))
    canvas.alpha_composite(product_tilted, (product_x, product_y))

    product_bbox = (
        product_x, product_y,
        product_x + product_tilted.width,
        product_y + product_tilted.height,
    )

    # --- Prop (ingredient) ---
    if prop_cutout_path and prop_cutout_path.exists():
        prop = Image.open(prop_cutout_path).convert("RGBA")
        prop_target_h = int(canvas_h * 0.22)
        pscale = prop_target_h / prop.height
        prop = prop.resize((int(prop.width * pscale), prop_target_h), Image.LANCZOS)
        # Right-side, partially overlapping base of jar
        prop_x = product_x + product_tilted.width - int(prop.width * 0.35)
        prop_y = product_zone_bottom - prop.height - int(canvas_h * 0.02)
        prop_shadow = _make_drop_shadow(prop, blur=18, opacity=75)
        canvas.alpha_composite(prop_shadow, (prop_x - 4, prop_y + 8))
        canvas.alpha_composite(prop, (prop_x, prop_y))

    _typeset_common(canvas, copy, brand, show_ingredient_name, product_bbox)
    _save(canvas, output_path)

    return CompositedStatic(
        output_path=str(output_path),
        width=canvas_w,
        height=canvas_h,
        template_used="B",
        product_bbox_xyxy=product_bbox,
    )


# ---------- Shared typography layer ----------

def _typeset_common(
    canvas: Image.Image,
    copy: CopyDeck,
    brand: BrandSpec,
    show_ingredient_name: str | None,
    product_bbox: tuple[int, int, int, int] | None,
) -> None:
    canvas_w, canvas_h = canvas.size
    on_dark = brand.background_mood in ("dark_moody",)
    text_color = "#FFFFFF" if on_dark else COLORS["text_primary"]
    secondary_color = "#DDDDDD" if on_dark else COLORS["text_secondary"]

    # Logo
    draw_wordmark(canvas, position="top-left", on_dark=on_dark, width_ratio=0.13)

    # Headline — auto-fit so it renders as 1–2 lines without truncation.
    headline_x = int(canvas_w * 0.05)
    headline_max_w = int(canvas_w * (0.55 if show_ingredient_name else 0.90))
    headline_bottom_y = _draw_auto_headline(
        canvas,
        text=copy.headline,
        xy=(headline_x, int(canvas_h * 0.12)),
        max_width=headline_max_w,
        max_lines=2,
        color=text_color,
    )

    # Oversized ingredient name on the right — OPT-IN only (ingredient claim type)
    if show_ingredient_name:
        draw_text_block(
            canvas,
            show_ingredient_name.upper(),
            xy=(int(canvas_w * 0.55), int(canvas_h * 0.22)),
            role="headline_bold",
            size_bucket="hero_headline",
            color=text_color,
            max_width=int(canvas_w * 0.40),
            max_lines=2,
            align="right",
        )

    # Subhead — directly under headline, full width, ABOVE the product zone.
    # No side-by-side squeeze, no competition with product placement.
    if copy.subhead:
        sub_y = headline_bottom_y + int(canvas_h * 0.015)  # small gap under headline
        # Full canvas width minus margins. If ingredient name is shown, respect it.
        sub_max_w = int(canvas_w * (0.55 if show_ingredient_name else 0.90))
        draw_text_block(
            canvas,
            copy.subhead,
            xy=(headline_x, sub_y),
            role="body",
            size_bucket="descriptor",
            color=secondary_color,
            max_width=sub_max_w,
            max_lines=2,
        )

    # Separator rule + bottom strip
    if copy.bottom_strip:
        if not on_dark:
            rule_y = int(canvas_h * 0.885)
            draw = ImageDraw.Draw(canvas, "RGBA")
            margin = int(canvas_w * 0.06)
            draw.line(
                [(margin, rule_y), (canvas_w - margin, rule_y)],
                fill=(0, 0, 0, 40),
                width=2,
            )
        strip_h = scaled_size("bottom_strip", canvas_w)
        strip_y = int(canvas_h * 0.93) - strip_h // 2
        draw_bottom_strip(
            canvas,
            copy.bottom_strip[:3],
            y=strip_y,
            color=text_color,
        )


# ---------- Helpers ----------

def _draw_auto_headline(
    canvas: Image.Image,
    *,
    text: str,
    xy: tuple[int, int],
    max_width: int,
    max_lines: int,
    color: str,
) -> int:
    """Find the largest size that fits `text` in `max_lines`. Returns the y-coordinate
    where the headline ended (for placing subhead below it)."""
    canvas_w = canvas.width
    font_path = resolve_font(FONT_ROLES["headline_bold"])
    if font_path is None:
        # Rough fallback — draw_text_block doesn't return bottom, so estimate.
        draw_text_block(
            canvas,
            text,
            xy=xy,
            role="headline_bold",
            size_bucket="hero_headline",
            color=color,
            max_width=max_width,
            max_lines=max_lines,
        )
        return xy[1] + int(canvas.height * 0.10)

    min_px = int(54 * canvas_w / 1080)
    max_px = int(96 * canvas_w / 1080)

    chosen_size = min_px
    for size in range(max_px, min_px - 1, -2):
        font = ImageFont.truetype(str(font_path), size=size)
        lines = _wrap_lines(text, font, max_width)
        if len(lines) <= max_lines:
            chosen_size = size
            break

    font = ImageFont.truetype(str(font_path), size=chosen_size)
    lines = _wrap_lines(text, font, max_width)[:max_lines]
    draw = ImageDraw.Draw(canvas)
    x, y = xy
    line_height = int(chosen_size * 1.05)
    for line in lines:
        draw.text((x, y), line, font=font, fill=color)
        y += line_height
    return y


def _wrap_lines(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
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
    return lines


def _make_drop_shadow(src: Image.Image, *, blur: int = 20, opacity: int = 90) -> Image.Image:
    alpha = src.split()[-1]
    layer = Image.new("RGBA", src.size, (0, 0, 0, 0))
    solid = Image.new("RGBA", src.size, (0, 0, 0, opacity))
    layer.paste(solid, (0, 0), alpha)
    return layer.filter(ImageFilter.GaussianBlur(blur))


def _save(canvas: Image.Image, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output_path, "PNG", optimize=True)

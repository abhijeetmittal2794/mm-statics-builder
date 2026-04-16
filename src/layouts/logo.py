"""Logo rendering.

Primary path: paste the real MM wordmark PNG from src/brand/assets/logo.png.
Fallback: render 'man matters®' typographically (used only if the PNG is missing).

For dark backgrounds, the black-on-transparent logo is recolored to white
in memory — no separate white-variant file needed.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from ..brand.pack import resolve_font
from ..brand.tokens import FONT_ROLES

LOGO_PATH = Path(__file__).resolve().parents[1] / "brand" / "assets" / "logo.png"


def draw_wordmark(
    img: Image.Image,
    *,
    position: str = "top-left",
    on_dark: bool = False,
    width_ratio: float = 0.13,
) -> None:
    """Stamp the Man Matters wordmark onto `img`."""
    if LOGO_PATH.exists():
        _paste_logo_image(img, position=position, on_dark=on_dark, width_ratio=width_ratio)
    else:
        _draw_logo_text(img, position=position, on_dark=on_dark, width_ratio=width_ratio)


def _paste_logo_image(
    img: Image.Image,
    *,
    position: str,
    on_dark: bool,
    width_ratio: float,
) -> None:
    logo = Image.open(LOGO_PATH).convert("RGBA")
    # Trim any transparent padding so width_ratio is measured on the actual mark
    logo = _trim_transparent(logo)

    target_w = int(img.width * width_ratio)
    scale = target_w / logo.width
    target_h = max(1, int(logo.height * scale))
    logo = logo.resize((target_w, target_h), Image.LANCZOS)

    if on_dark:
        logo = _recolor_alpha_to(logo, rgb=(255, 255, 255))

    x, y = _anchor(img, position, logo.size)
    img.alpha_composite(logo, (x, y))


def _draw_logo_text(
    img: Image.Image,
    *,
    position: str,
    on_dark: bool,
    width_ratio: float,
) -> None:
    """Fallback: render 'man matters®' in bold Inter. Only used if logo.png missing."""
    color = "#FFFFFF" if on_dark else "#000000"
    text = "man matters®"
    target_w = int(img.width * width_ratio)

    path = resolve_font(FONT_ROLES["headline_bold"])
    if path is None:
        from PIL import ImageFont
        font = ImageFont.load_default()
        ImageDraw.Draw(img).text(_anchor_tl(img, position), text, fill=color, font=font)
        return

    from PIL import ImageFont
    lo, hi = 10, 200
    best = 24
    while lo <= hi:
        mid = (lo + hi) // 2
        f = ImageFont.truetype(str(path), size=mid)
        w = f.getbbox(text)[2]
        if w <= target_w:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    font = ImageFont.truetype(str(path), size=best)
    ImageDraw.Draw(img).text(_anchor_tl(img, position), text, fill=color, font=font)


# ---------- helpers ----------

def _trim_transparent(logo: Image.Image) -> Image.Image:
    bbox = logo.getbbox()
    return logo.crop(bbox) if bbox else logo


def _recolor_alpha_to(logo: Image.Image, rgb: tuple[int, int, int]) -> Image.Image:
    """Keep the original alpha channel, swap RGB for the given color."""
    alpha = logo.split()[-1]
    solid = Image.new("RGBA", logo.size, rgb + (255,))
    solid.putalpha(alpha)
    return solid


def _anchor(img: Image.Image, position: str, size: tuple[int, int]) -> tuple[int, int]:
    margin = int(0.04 * img.width)
    w, h = size
    if position == "top-left":
        return (margin, margin)
    if position == "top-right":
        return (img.width - margin - w, margin)
    if position == "bottom-left":
        return (margin, img.height - margin - h)
    return (margin, margin)


def _anchor_tl(img: Image.Image, position: str) -> tuple[int, int]:
    """Top-left anchor for text fallback (no size probe)."""
    margin = int(0.04 * img.width)
    if position == "top-right":
        return (img.width - margin - int(0.13 * img.width), margin)
    if position == "bottom-left":
        return (margin, img.height - margin - int(0.04 * img.height))
    return (margin, margin)

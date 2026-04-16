"""Brand pack loader: exposes design.md content + exemplar statics to the agents.

The markdown is injected verbatim into Claude prompts as system/user context.
Exemplar images are referenced by path and passed as image blocks.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DESIGN_MD_PATH = PROJECT_ROOT / "design.md"
TRAINING_IMAGES_DIR = PROJECT_ROOT / "Training Images"
PRODUCT_PHOTOS_DIR = PROJECT_ROOT / "Product Photos"
FONTS_DIR = PROJECT_ROOT / "src" / "fonts"


def load_design_guide() -> str:
    if not DESIGN_MD_PATH.exists():
        raise FileNotFoundError(f"design.md not found at {DESIGN_MD_PATH}")
    return DESIGN_MD_PATH.read_text(encoding="utf-8")


def list_exemplar_statics(max_count: int = 12) -> list[Path]:
    """Return up to N training images to include as visual references."""
    if not TRAINING_IMAGES_DIR.exists():
        return []
    images = sorted(
        p for p in TRAINING_IMAGES_DIR.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )
    return images[:max_count]


def product_asset(name: str) -> Optional[Path]:
    """Resolve product asset by filename (e.g., 'Shilajit 60.png')."""
    p = PRODUCT_PHOTOS_DIR / name
    return p if p.exists() else None


def resolve_font(font_files: list[str]) -> Optional[Path]:
    """Return first existing font from preference chain."""
    for name in font_files:
        candidate = FONTS_DIR / name
        if candidate.exists():
            return candidate
    return None

"""Product asset registry.

Tags each file in Product Photos/ by role so the pipeline can pick the right image
for the right purpose:

  - "hero_silhouette": the clean cutout used for compositing
  - "gummy": loose gummies, used in usage/upgrade templates
  - "label_reference": zoomed front-of-pack shots, used as label-fidelity references
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..brand.pack import PRODUCT_PHOTOS_DIR


@dataclass(frozen=True)
class ProductAsset:
    path: Path
    role: str
    notes: str = ""


def _find_screenshot(partial: str) -> Path:
    """Match screenshot filenames despite macOS Unicode quirks (narrow no-break space etc.)."""
    for f in PRODUCT_PHOTOS_DIR.iterdir():
        if partial in f.name.replace("\u202f", " "):
            return f
    return PRODUCT_PHOTOS_DIR / partial  # fallback to literal


REGISTRY: list[ProductAsset] = [
    ProductAsset(
        path=PRODUCT_PHOTOS_DIR / "Shilajit 60.png",
        role="hero_silhouette",
        notes="Main 60-count Shilajit Gummies jar, 2000x2000",
    ),
    ProductAsset(
        path=PRODUCT_PHOTOS_DIR / "Gummy-1.png",
        role="gummy",
        notes="Loose amber gummies",
    ),
    ProductAsset(
        path=_find_screenshot("Screenshot 2026-04-14 at 8.35.38 PM.png"),
        role="label_reference",
    ),
    ProductAsset(
        path=_find_screenshot("Screenshot 2026-04-15 at 8.14.04 AM.png"),
        role="label_reference",
    ),
    ProductAsset(
        path=_find_screenshot("Screenshot 2026-04-15 at 8.14.27 AM.png"),
        role="label_reference",
    ),
    ProductAsset(
        path=_find_screenshot("Screenshot 2026-04-15 at 8.14.34 AM.png"),
        role="label_reference",
    ),
    ProductAsset(
        path=_find_screenshot("Screenshot 2026-04-15 at 8.15.22 AM.png"),
        role="label_reference",
    ),
]


def hero_silhouette() -> Path:
    for a in REGISTRY:
        if a.role == "hero_silhouette" and a.path.exists():
            return a.path
    raise FileNotFoundError("No hero_silhouette asset in registry.")


def gummy() -> Path | None:
    for a in REGISTRY:
        if a.role == "gummy" and a.path.exists():
            return a.path
    return None


def label_references(max_count: int = 4) -> list[Path]:
    refs = [a.path for a in REGISTRY if a.role == "label_reference" and a.path.exists()]
    return refs[:max_count]

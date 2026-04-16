"""Prop (ingredient) library.

Maps ingredient keywords to real photographs in Training Images/.
Used by the Scene Integrator to hand Nano Banana Pro authentic ingredient
references rather than asking it to imagine shilajit/ashwagandha/etc.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..brand.pack import PROJECT_ROOT

TRAINING_IMAGES_DIR = PROJECT_ROOT / "Training Images"


@dataclass(frozen=True)
class Prop:
    keyword: str
    display_name: str
    image_path: Path
    description: str


# Add new ingredients here as the product line grows.
PROPS: list[Prop] = [
    Prop(
        keyword="shilajit",
        display_name="Shilajit",
        image_path=TRAINING_IMAGES_DIR / "Shilajit.png",
        description="Dark glossy rocky mineral chunks, Himalayan origin",
    ),
    Prop(
        keyword="ashwagandha",
        display_name="KSM-66® Ashwagandha",
        image_path=TRAINING_IMAGES_DIR / "Ashwagandha.png",
        description="Dried pale beige root sticks, typically in a glass bowl",
    ),
    Prop(
        keyword="chicory",
        display_name="Chicory Root",
        image_path=TRAINING_IMAGES_DIR / "Chicory root.png",
        description="Large beige chicory root stick, sometimes with purple flower",
    ),
    Prop(
        keyword="black pepper",
        display_name="Black Pepper",
        image_path=TRAINING_IMAGES_DIR / "Black Pepper.png",
        description="Whole black peppercorns",
    ),
]


def find_props_for_brief(audience_hook: str, mood_keywords: list[str]) -> list[Prop]:
    """Return props that match the brief. Searches hook + keywords case-insensitively."""
    haystack = " ".join([audience_hook] + mood_keywords).lower()
    matched = [p for p in PROPS if p.keyword in haystack and p.image_path.exists()]
    return matched


def get_prop(keyword: str) -> Prop | None:
    for p in PROPS:
        if p.keyword == keyword.lower() and p.image_path.exists():
            return p
    return None


def default_prop() -> Prop | None:
    """Safe default — Shilajit is always relevant for this product line."""
    return get_prop("shilajit")

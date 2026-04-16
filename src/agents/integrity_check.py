"""Label-integrity drift detection.

Compares the product region in the integrated (harmonized) image against the
clean product cutout. Uses pHash + dHash — both are structure-sensitive but
tolerant of lighting/color shifts, which is exactly what we want: detect when
the label text or silhouette warped, while ignoring intentional relighting.

If drift exceeds threshold, the caller should fall back to pure alpha composite.
"""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

import imagehash
from PIL import Image


def check_product_drift(
    *,
    reference_cutout: Path,
    integrated_image: Path,
    threshold: int = 18,
) -> Tuple[float, bool]:
    """Return (drift_score, passed).

    drift_score = sum of Hamming distances on pHash and dHash.
    passed = drift_score <= threshold.

    We can't know exactly where the model placed the product in the integrated
    image without detection, so we approximate by comparing a resized normalized
    product-sized region. The hashes are size-invariant enough that this works
    as a coarse "did the label warp?" check.

    For a production-grade check, wire in a light object detector (YOLO or a
    vision-model bbox call) to localize the product before hashing.
    """
    ref_img = Image.open(reference_cutout).convert("RGB")
    integrated = Image.open(integrated_image).convert("RGB")

    # Normalize both to a square for hashing; the hashes are designed to be
    # invariant to aspect/resize within reason.
    ref_sq = _fit_square(ref_img, 512)
    int_sq = _fit_square(integrated, 512)

    ref_phash = imagehash.phash(ref_sq)
    ref_dhash = imagehash.dhash(ref_sq)
    int_phash = imagehash.phash(int_sq)
    int_dhash = imagehash.dhash(int_sq)

    drift = (ref_phash - int_phash) + (ref_dhash - int_dhash)
    passed = drift <= threshold
    return float(drift), passed


def _fit_square(img: Image.Image, side: int) -> Image.Image:
    """Resize preserving aspect, pad to square with neutral background."""
    img = img.copy()
    img.thumbnail((side, side), Image.LANCZOS)
    square = Image.new("RGB", (side, side), (240, 240, 240))
    x = (side - img.width) // 2
    y = (side - img.height) // 2
    square.paste(img, (x, y))
    return square

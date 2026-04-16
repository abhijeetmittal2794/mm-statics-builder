"""Approved-outputs memory.

Outputs rated >= 8 are saved here with metadata. On future runs, the most recent
approved outputs are fed as extra style references to Nano Banana Pro, creating a
feedback loop: good outputs improve future outputs.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

APPROVED_DIR = Path(__file__).resolve().parents[2] / "outputs" / "approved"


def save_approved(image_path: str | Path, metadata: dict) -> Path:
    APPROVED_DIR.mkdir(parents=True, exist_ok=True)
    src = Path(image_path)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = f"{ts}_{src.stem}"
    dest_img = APPROVED_DIR / f"{stem}.png"
    dest_meta = APPROVED_DIR / f"{stem}.json"

    shutil.copy2(src, dest_img)
    metadata["source_path"] = str(src)
    metadata["approved_at"] = datetime.now().isoformat()
    dest_meta.write_text(json.dumps(metadata, indent=2, default=str))
    return dest_img


def get_approved_refs(max_count: int = 3) -> list[Path]:
    """Most recent approved PNGs, newest first."""
    if not APPROVED_DIR.exists():
        return []
    pngs = sorted(APPROVED_DIR.glob("*.png"), reverse=True)
    return pngs[:max_count]


def list_approved() -> list[dict]:
    if not APPROVED_DIR.exists():
        return []
    items = []
    for meta_path in sorted(APPROVED_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(meta_path.read_text())
            data["image_file"] = meta_path.stem + ".png"
            items.append(data)
        except Exception:
            continue
    return items

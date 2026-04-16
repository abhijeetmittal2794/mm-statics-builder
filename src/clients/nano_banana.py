"""Nano Banana Pro (Gemini 3 Pro Image) wrapper.

The scene generator calls this to produce:
  (a) a backdrop scene with negative space shaped for the product silhouette
  (b) optionally, a contact shadow layer for realistic product grounding

IMPORTANT: We never ask this model to render the product, the logo, or any copy text.
Scene only. Product is composited downstream from real pixels.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types
from google.genai.errors import ClientError

_client: Optional[genai.Client] = None

# Ordered list of fallbacks — tried in order if the configured model isn't accessible.
FALLBACK_MODELS = [
    "gemini-3-pro-image-preview",
    "gemini-2.5-flash-image-preview",
    "gemini-2.5-flash-image",
]


def client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY not set. Copy .env.example to .env.")
        _client = genai.Client(api_key=api_key)
    return _client


def _model() -> str:
    return os.environ.get("NANO_BANANA_MODEL", "gemini-3-pro-image")


def generate_scene(
    *,
    prompt: str,
    reference_images: list[Path] | None = None,
    out_path: Path,
    aspect_ratio: str = "4:5",
) -> Path:
    """Generate a scene image.

    Args:
        prompt: Textual scene description. Must NOT describe product or copy.
        reference_images: Brand exemplars and prop refs. Model uses these for style/mood only.
        out_path: Where to save the resulting PNG.
        aspect_ratio: One of "1:1", "4:5", "9:16", "16:9".
    """
    parts: list = [prompt]
    for p in reference_images or []:
        if not p.exists():
            continue
        parts.append(
            types.Part.from_bytes(
                data=p.read_bytes(),
                mime_type=_mime(p),
            )
        )

    # Try configured model first, then fallbacks. Skip duplicates.
    tried: list[str] = []
    models_to_try = [_model()] + [m for m in FALLBACK_MODELS if m != _model()]
    last_err: Exception | None = None

    for model_id in models_to_try:
        try:
            resp = client().models.generate_content(
                model=model_id,
                contents=parts,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
                ),
            )
        except ClientError as e:
            tried.append(f"{model_id} → {getattr(e, 'code', '?')}")
            last_err = e
            continue

        for candidate in resp.candidates or []:
            for part in candidate.content.parts:
                inline = getattr(part, "inline_data", None)
                if inline and inline.data:
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_bytes(inline.data)
                    return out_path

        tried.append(f"{model_id} → no image in response")

    raise RuntimeError(
        "Image generation failed for all candidate models.\n"
        + "\n".join(f"  - {t}" for t in tried)
        + (f"\nLast error: {last_err}" if last_err else "")
    )


def edit_image(
    *,
    prompt: str,
    input_images: list[Path],
    out_path: Path,
    aspect_ratio: str = "4:5",
) -> Path:
    """Image-edit mode — compose/harmonize multiple inputs into a single output.

    Used by the Scene Integrator to place the product cutout + prop photos into
    the generated backdrop with unified lighting. The first image in input_images
    is conventionally the backdrop; subsequent images are objects to place.
    """
    parts: list = [prompt]
    for p in input_images:
        if not p.exists():
            continue
        parts.append(types.Part.from_bytes(data=p.read_bytes(), mime_type=_mime(p)))

    tried: list[str] = []
    models_to_try = [_model()] + [m for m in FALLBACK_MODELS if m != _model()]
    last_err: Exception | None = None

    for model_id in models_to_try:
        try:
            resp = client().models.generate_content(
                model=model_id,
                contents=parts,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
                ),
            )
        except ClientError as e:
            tried.append(f"{model_id} → {getattr(e, 'code', '?')}")
            last_err = e
            continue

        for candidate in resp.candidates or []:
            for part in candidate.content.parts:
                inline = getattr(part, "inline_data", None)
                if inline and inline.data:
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_bytes(inline.data)
                    return out_path
        tried.append(f"{model_id} → no image in response")

    raise RuntimeError(
        "Image editing failed for all candidate models.\n"
        + "\n".join(f"  - {t}" for t in tried)
        + (f"\nLast error: {last_err}" if last_err else "")
    )


def list_image_models() -> list[str]:
    """Return model IDs on this key that support image output.

    Used by `python cli.py models` to help pick the right NANO_BANANA_MODEL.
    """
    ids: list[str] = []
    for m in client().models.list():
        name = getattr(m, "name", "") or ""
        supported = getattr(m, "supported_actions", None) or getattr(
            m, "supported_generation_methods", None
        ) or []
        # Image-capable Gemini image models typically have 'image' in the name
        if "image" in name.lower():
            ids.append(name.replace("models/", ""))
    return sorted(set(ids))


def _mime(p: Path) -> str:
    s = p.suffix.lower()
    return {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(s, "image/png")

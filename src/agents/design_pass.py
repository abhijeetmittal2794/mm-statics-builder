"""Agent 5d: Design Pass.

Takes the restamped image (backdrop + jar with correct label) and adds the
typography layer — headline, subhead, bottom strip — via Nano Banana Pro.

Why NBP instead of code: typography placement is a design judgment, not a
rule-following exercise. NBP composes type against the scene rather than
following hardcoded zone rules. The result reads as "designed" not "placed".

The real 'man matters®' wordmark is always stamped by code after NBP finishes,
guaranteeing brand-mark fidelity. Headline/subhead/strip are NBP's work, and
the downstream typography verifier checks them character-by-character.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from PIL import Image

from ..clients.nano_banana import edit_image
from ..layouts.logo import draw_wordmark
from ..models import BrandSpec, BuildInput, CopyDeck

OUTPUTS_DIR = Path(__file__).resolve().parents[2] / "outputs"


def run(
    *,
    inp: BuildInput,
    brand: BrandSpec,
    restamped_path: Path,
    aspect_ratio: str = "4:5",
) -> Path:
    prompt = _build_prompt(inp.copy_deck, brand)
    out_path = OUTPUTS_DIR / "designed" / f"designed_{uuid.uuid4().hex[:10]}.png"
    edit_image(
        prompt=prompt,
        input_images=[restamped_path],
        out_path=out_path,
        aspect_ratio=aspect_ratio,
    )

    # Stamp the real MM wordmark over whatever NBP drew as a logo.
    # NBP's logo-text attempt is expected to be visually similar; our stamp
    # guarantees the exact custom wordmark.
    on_dark = brand.background_mood in ("dark_moody",)
    img = Image.open(out_path).convert("RGBA")
    draw_wordmark(img, position="top-left", on_dark=on_dark, width_ratio=0.13)
    img.convert("RGB").save(out_path, "PNG", optimize=True)
    return out_path


def _build_prompt(copy: CopyDeck, brand: BrandSpec) -> str:
    on_dark = brand.background_mood in ("dark_moody",)
    text_color = "pure white" if on_dark else "near-black (#1C1C1C)"
    secondary_color = "light grey" if on_dark else "medium grey (#5A5A5A)"

    subhead_line = f'- Subhead: "{copy.subhead}"' if copy.subhead else "- No subhead."
    bottom_strip = (
        f'- Bottom strip (three items, separated by " | " vertical pipe): '
        + " | ".join(f'"{item}"' for item in copy.bottom_strip)
        if copy.bottom_strip
        else "- No bottom strip."
    )
    cta_line = f'- CTA (small pill button at bottom): "{copy.cta}"' if copy.cta else "- No CTA."

    return f"""You are adding TYPOGRAPHY to a Man Matters Shilajit Gummies static advertisement. The input image already contains the backdrop and the product jar. Your only job is to add the copy elements onto this image in a designed composition — as a skilled editorial advertising art director would.

BRAND TYPOGRAPHY SYSTEM:
- Typeface family: clean modern geometric sans-serif (reference: Inter, GT America, Neue Haas Grotesk). NEVER serif.
- Headline: very bold (800–900 weight), title case, tight leading.
- Subhead: regular (400 weight), sentence case, 50–60% of headline size.
- Bottom strip: semi-bold (600 weight), small.
- Primary text color: {text_color}.
- Secondary text color: {secondary_color}.

COPY TO RENDER — render EXACTLY as written. Do not paraphrase, rearrange, abbreviate, or omit any word. Punctuation and case must match:
- Headline: "{copy.headline}"
{subhead_line}
{bottom_strip}
{cta_line}

COMPOSITION DIRECTION (art-direct these, don't follow them mechanically):
- Leave the top-left corner (~12% of canvas width) completely empty for a logo that will be stamped by a later step. Do not place any headline text in that zone.
- Headline: upper portion of the canvas, left-aligned, sized large enough to feel like the hero. Break into two lines if natural. Do NOT truncate or cut off ANY word.
- Subhead: directly below the headline with a small gap, at about 55% of the headline's size.
- Bottom strip: positioned at the very bottom with a thin horizontal rule above it at roughly 88% canvas height. Center the strip. Use " | " as a separator.
- Do NOT place any copy on, overlapping, or crossing the product jar.
- Leave clean breathing room between elements.

HARD RULES — violation is disqualifying:
- Render EVERY word exactly as written above. No substitutions, no synonyms, no missing words, no extra words.
- NO serif fonts anywhere.
- DO NOT alter, move, recolor, or draw over the product jar.
- DO NOT alter the backdrop.
- DO NOT add extra copy, claims, icons, taglines, subtitles, or decorative flourishes beyond the items listed above.
- Every rendered character must be crisp, readable, and correctly formed.

STYLE: premium editorial advertising — clean, minimal, confident, modern-masculine. Indian D2C wellness brand tone.

OUTPUT: the same input image, now with typography added as described. Same dimensions, same scene, same jar. Only typography is added.
"""

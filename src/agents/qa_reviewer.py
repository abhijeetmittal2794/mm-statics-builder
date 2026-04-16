"""Agent 7: QA Reviewer.

Two-phase check:
  Phase 1 — Code-level geometric and content checks (deterministic, fast, free).
  Phase 2 — LLM vision review with a tight, measurable rubric (subjective judgment).

Phase 1 runs first and can emit blockers before we spend LLM tokens. Phase 2
fills in the qualitative judgment (aesthetic, hierarchy, premium feel).
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from ..clients.anthropic_client import call_claude
from ..models import (
    BrandSpec,
    CompositedStatic,
    ParsedBrief,
    QACheck,
    QAReport,
)
from ..product.registry import label_references
from ._common import MM_BRAND_PREAMBLE, parse_model


SYSTEM = MM_BRAND_PREAMBLE + """
Your specific role: QA Reviewer (Phase 2 — subjective judgment).

You are shown:
  1. The final composited static (image 1)
  2. The hero product photo (image 2)
  3. Label close-ups of the actual pack (images 3+) — ground truth for label text

You evaluate the final against these subjective checks and return a QAReport.
Each check is true/false with a short note and a severity.

SUBJECTIVE CHECKS (you own these):
  - "single_product": Is there EXACTLY ONE jar in the final image? Multiple jars,
    a ghosted background jar, a mirrored jar, or any secondary instance of the
    product is a failure. [blocker]
  - "label_integrity": Does the product label in the final match the close-ups
    exactly? Compare word-for-word. This should almost always pass (the product
    is composited from real pixels via a restamp step); fail only on obvious
    post-compositing damage such as heavy occlusion or colour corruption. [blocker]
  - "product_orientation": Is the jar upright and facing forward? Not lying down,
    not at extreme angles (>10° tilt fails). [blocker]
  - "no_hallucinated_text": Is all typography clean and from the copy deck only?
    No garbled letters, no model-invented words or claims. [blocker]
  - "palette_adherence": Does the scene stay within MM brand colors — no purple,
    neon, off-brand tones? [major]
  - "premium_minimal": Does it read as premium and minimal — not cluttered,
    not busy, not amateur? Compare mental model: would a top Indian D2C brand ship this? [major]
  - "composition_hierarchy": Is there ONE clear hero message? Does the eye know
    where to land first? [major]
  - "lighting_consistency": Do product and prop shadows match the backdrop's
    light direction? Does everything look shot together? [major]
  - "whitespace_balance": Is there breathing room, or does copy crowd the product? [minor]

Score: 0–1 weighted. Any blocker fail halves the score. Two major fails also halve.

retry target (only set if overall_pass is false):
  - "creative_director" if the concept itself is fundamentally wrong
  - "scene_generator" if the backdrop is off-brand
  - "compositor" if layout, placement, or typography is the issue

Return ONLY JSON:
{
  "overall_pass": true|false,
  "score": 0.0-1.0,
  "checks": [{"name": "...", "passed": true|false, "severity": "blocker"|"major"|"minor", "note": "..."}],
  "critiques_for_retry": ["...", ...],
  "target_agent_for_retry": "creative_director"|"scene_generator"|"compositor"|null
}
"""


def run(
    *,
    final: CompositedStatic,
    product_reference_path: Path,
    brief: ParsedBrief,
    brand: BrandSpec,
) -> QAReport:
    # Phase 1 — deterministic checks
    phase1_checks = _phase1_geometry(final)

    # If Phase 1 has a blocker, we can stop early.
    if any(c.severity == "blocker" and not c.passed for c in phase1_checks):
        return QAReport(
            overall_pass=False,
            score=0.0,
            checks=phase1_checks,
            critiques_for_retry=[c.note for c in phase1_checks if not c.passed],
            target_agent_for_retry="compositor",
        )

    # Phase 2 — LLM judgment
    label_refs = label_references(max_count=3)
    user_text = (
        "Review the final static (image 1) against the hero product (image 2) "
        f"and {len(label_refs)} label close-up reference(s).\n\n"
        f"Brief claim type: {brief.claim_type}\n"
        f"Chosen template: {brand.chosen_template}\n"
        f"Background mood: {brand.background_mood}\n"
        f"Palette: {brand.primary_palette_hex}\n\n"
        "Emit the QAReport JSON."
    )
    images = [Path(final.output_path), product_reference_path] + label_refs
    response = call_claude(
        system=SYSTEM,
        user_text=user_text,
        image_paths=images,
        temperature=0.2,
    )
    report = parse_model(response, QAReport)
    # Merge Phase 1 checks in so the report carries both layers
    report.checks = phase1_checks + report.checks
    return report


# ---------- Phase 1: deterministic checks ----------

def _phase1_geometry(final: CompositedStatic) -> list[QACheck]:
    """Fast, free, deterministic checks on the final image."""
    checks: list[QACheck] = []
    path = Path(final.output_path)
    if not path.exists():
        checks.append(QACheck(
            name="output_exists",
            passed=False,
            severity="blocker",
            note="Final static file not written.",
        ))
        return checks

    img = Image.open(path)
    w, h = img.size

    # Canvas dimensions match expected
    checks.append(QACheck(
        name="canvas_dimensions_match",
        passed=(w == final.width and h == final.height),
        severity="minor",
        note=f"Actual {w}x{h} vs expected {final.width}x{final.height}",
    ))

    # Product bbox is inside canvas
    if final.product_bbox_xyxy and any(final.product_bbox_xyxy):
        x0, y0, x1, y1 = final.product_bbox_xyxy
        inside = (0 <= x0 < x1 <= w) and (0 <= y0 < y1 <= h)
        checks.append(QACheck(
            name="product_within_canvas",
            passed=inside,
            severity="blocker",
            note=f"Product bbox {final.product_bbox_xyxy} in canvas {w}x{h}",
        ))

        # Bottom strip sits at ~0.90–0.97 of canvas height; product must not
        # extend into this zone (blocker-ish — minor if barely).
        strip_top = int(h * 0.88)
        product_overlaps_strip = y1 > strip_top
        checks.append(QACheck(
            name="product_clear_of_bottom_strip",
            passed=not product_overlaps_strip,
            severity="major" if product_overlaps_strip else "minor",
            note=f"Product bottom={y1}, strip begins at {strip_top}",
        ))

        # Headline zone is top ~28% — product must not intrude
        headline_bottom = int(h * 0.28)
        product_in_headline = y0 < headline_bottom
        checks.append(QACheck(
            name="product_below_headline_zone",
            passed=not product_in_headline,
            severity="major" if product_in_headline else "minor",
            note=f"Product top={y0}, headline zone ends at {headline_bottom}",
        ))

    return checks

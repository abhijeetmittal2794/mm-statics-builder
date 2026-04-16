"""Option B: Our compositing pipeline, stripped to essentials.

4 NBP calls, one code step, no retries, no QA:
  1. Scene Generator → backdrop only
  2. Scene Integrator → jar placed with shadow
  3. Product Restamp → original jar pixels (code — diff detection)
  4. Design Pass → NBP renders typography on restamped image
"""
from pathlib import Path

from dotenv import load_dotenv

from src.clients.nano_banana import generate_scene, edit_image
from src.agents.product_restamp import _detect_jar_bbox_via_diff, _stamp
from src.product.prep import prepare_cutout
from src.product.registry import hero_silhouette
from src.brand.pack import list_exemplar_statics

load_dotenv()

PRODUCT = Path("Product Photos/Shilajit 60.png")
OUT_DIR = Path("outputs/compare")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------- Step 1: Backdrop ----------
print("Step 1/4 — Backdrop…")
BACKDROP = OUT_DIR / "B_step1_backdrop.png"
generate_scene(
    prompt="""A clean premium product-photography backdrop. Warm beige/cream surface (#F5F0E8),
soft studio lighting from upper-right (~4500K), subtle shallow depth of field.
NO objects, NO text, NO product — just the empty surface and light.
Premium editorial aesthetic, Indian D2C wellness brand tone.""",
    reference_images=list_exemplar_statics(max_count=3),
    out_path=BACKDROP,
    aspect_ratio="4:5",
)
print(f"  → {BACKDROP}")

# ---------- Step 2: Integrate product ----------
print("Step 2/4 — Integrate product…")
CUTOUT = prepare_cutout(hero_silhouette())
INTEGRATED = OUT_DIR / "B_step2_integrated.png"
edit_image(
    prompt="""Place the product jar (image 2) onto the backdrop (image 1).

POSITION: center-right, upright, facing camera. One jar only — not two.
SHADOW: soft contact shadow under the base, grounded to the surface.
LIGHTING: match the backdrop's key light. Atmospheric cohesion so it looks shot together.
NO text, NO extra objects, NO humans. Just the jar on the surface with natural shadow.""",
    input_images=[BACKDROP, CUTOUT],
    out_path=INTEGRATED,
    aspect_ratio="4:5",
)
print(f"  → {INTEGRATED}")

# ---------- Step 3: Restamp ----------
print("Step 3/4 — Restamp (code)…")
RESTAMPED = OUT_DIR / "B_step3_restamped.png"
try:
    bbox = _detect_jar_bbox_via_diff(BACKDROP, INTEGRATED)
    print(f"  bbox detected: {bbox}")
except Exception as e:
    print(f"  diff detection failed ({e}), using fallback bbox")
    from PIL import Image
    w, h = Image.open(INTEGRATED).size
    cx, cy = int(w * 0.55), int(h * 0.55)
    pw, ph = int(w * 0.40), int(h * 0.55)
    bbox = (cx - pw // 2, cy - ph // 2, cx + pw // 2, cy + ph // 2)
_stamp(INTEGRATED, CUTOUT, bbox, RESTAMPED)
print(f"  → {RESTAMPED}")

# ---------- Step 4: Design pass ----------
print("Step 4/4 — Typography (NBP)…")
FINAL = OUT_DIR / "B_step4_final.png"
edit_image(
    prompt="""Add typography to this advertising static. The backdrop and product jar are already in the image. Add ONLY the copy elements:

COPY (render every word exactly):
- Logo: "man matters®" — top-left, small, lowercase bold sans-serif
- Headline: "Ancient Strength. Modern Convenience." — upper-left, very bold, 2 lines
- Subhead: "300 mg pure shilajit per serving, in a tasty chewable gummy." — below headline, lighter weight
- Bottom strip: "No Added Sugar  |  100% Natural  |  Clinically Tested" — centered at very bottom, small
- CTA: "Shop Now" — small black pill button below subhead
- Thin horizontal rule above the bottom strip

RULES:
- Sans-serif only (Inter / GT America style)
- Near-black text (#1C1C1C), grey subhead (#5A5A5A)
- Do NOT alter the product jar or backdrop
- Do NOT add any extra text, claims, or objects
- No text overlapping the jar

STYLE: premium, minimal, editorial.""",
    input_images=[RESTAMPED],
    out_path=FINAL,
    aspect_ratio="4:5",
)
print(f"  → {FINAL}")

print(f"\n✅ Compare:")
print(f"  Option A (one-shot):   outputs/compare/A_nano_oneshot.png")
print(f"  Option B (composite):  outputs/compare/B_step4_final.png")
print(f"  B intermediates:       outputs/compare/B_step*.png")

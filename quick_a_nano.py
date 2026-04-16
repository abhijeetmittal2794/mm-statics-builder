"""Option A: Let Nano Banana do EVERYTHING in one shot.

One single NBP call. Product reference + copy deck + brand guide → finished static.
No orchestrator, no restamp, no code typography, no QA. Just the model.
"""
from pathlib import Path

from dotenv import load_dotenv

from src.clients.nano_banana import edit_image

load_dotenv()

PRODUCT = Path("Product Photos/Shilajit 60.png")
OUT = Path("outputs/compare/A_nano_oneshot.png")

PROMPT = """You are creating a premium advertising static for Man Matters Shilajit Gummies.

PRODUCT: Image 1 is the exact product jar. You MUST include this jar in the output with its label, logo, silhouette, and every printed word preserved exactly as shown. The jar is matte black body with a white cap. ONE jar only — do not duplicate it.

COPY TO RENDER (render every word exactly — no paraphrasing, no omitting):
- Logo: "man matters®" — top-left, small lowercase bold sans-serif
- Headline: "Ancient Strength. Modern Convenience." — upper area, very bold, 2 lines, large
- Subhead: "300 mg pure shilajit per serving, in a tasty chewable gummy." — below headline, regular weight, smaller
- Bottom strip: "No Added Sugar  |  100% Natural  |  Clinically Tested" — centered at the very bottom, small, semi-bold
- CTA: "Shop Now" — small black pill button below the subhead

BRAND GUIDELINES:
- Background: warm beige/cream (#F5F0E8 to #EDE8DC), soft studio lighting from upper-right
- Text: near-black (#1C1C1C) for headlines, medium grey (#5A5A5A) for subhead
- Typography: clean geometric sans-serif like Inter or GT America. NO serif fonts.
- Aesthetic: premium, minimal, editorial product photography. Indian D2C wellness brand.
- Thin horizontal rule line above the bottom strip

COMPOSITION:
- Jar: center-right, upright, hero, facing camera. Takes up ~40-50% of the canvas height.
- Headline: upper-left third, bold, 2 lines
- Subhead: directly below headline, ~55% of headline size
- Clear breathing room between text elements and the product
- No text overlapping the jar

HARD RULES:
- Exactly ONE jar. Not two.
- Every word of copy rendered exactly as written above
- No extra text, claims, taglines, or decorations
- Sans-serif only
- No humans, hands, or figures

FORMAT: 4:5 aspect ratio. High resolution, sharp.
OUTPUT: a single finished advertising static ready to ship.
"""

if __name__ == "__main__":
    print("Generating Option A — Nano Banana one-shot…")
    edit_image(prompt=PROMPT, input_images=[PRODUCT], out_path=OUT, aspect_ratio="4:5")
    print(f"Done: {OUT}")

"""Hard-coded brand tokens extracted from design.md.

We keep these in code (not parsed from markdown) so downstream code is type-safe
and refactors are obvious. When design.md changes, update this file.
"""
from __future__ import annotations

# ---------- Colors ----------

COLORS = {
    "bg_warm_beige": "#F5F0E8",
    "bg_beige_alt": "#EDE8DC",
    "bg_cool_light_grey_a": "#E8E8E8",
    "bg_cool_light_grey_b": "#F2F2F2",
    "bg_dark_moody": "#2D2825",
    "bg_charcoal": "#1A1A1A",
    "bg_pure_white": "#FFFFFF",
    "jar_body": "#111111",
    "jar_cap": "#F0F0F0",
    "cta_bg": "#000000",
    "text_primary": "#1C1C1C",
    "text_secondary": "#5A5A5A",
    "strikethrough_grey": "#999999",
    "badge_bg": "#FFFFFF",
    "tick_green": "#3DAA5C",
    "star_gold": "#F5A623",
}

BACKGROUND_MOODS = {
    "warm_beige": ["#F5F0E8", "#EDE8DC"],
    "cool_light_grey": ["#E8E8E8", "#F2F2F2"],
    "dark_moody": ["#2D2825", "#1A1A1A"],
    "pure_white": ["#FFFFFF"],
    "mountain_sky": [],  # photographic
}

# ---------- Typography ----------
# Font file paths are resolved at runtime from src/fonts/.
# Map brand roles → font filenames. Fallback chain allows easy swaps.

FONT_ROLES = {
    "headline_bold": ["GTAmerica-Black.otf", "Inter-Black.ttf", "Arial-Black.ttf"],
    "headline_regular": ["GTAmerica-Regular.otf", "Inter-Regular.ttf", "Arial.ttf"],
    "body": ["DMSans-Regular.ttf", "Inter-Regular.ttf", "Arial.ttf"],
    "body_bold": ["DMSans-Bold.ttf", "Inter-Bold.ttf", "Arial-Bold.ttf"],
    "label_caps": ["DMSans-Medium.ttf", "Inter-Medium.ttf", "Arial.ttf"],
}

# Type scale at 1080×1080; scale proportionally for other canvases
TYPE_SCALE_1080 = {
    "hero_headline": {"min": 72, "max": 96},
    "subheadline": {"min": 40, "max": 52},
    "descriptor": {"min": 28, "max": 36},
    "eyebrow": {"min": 20, "max": 24},
    "cta": {"min": 32, "max": 38},
    "bottom_strip": {"min": 22, "max": 26},
}

# ---------- Formats ----------

CANVAS_SIZES = {
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
    "9:16": (1080, 1920),
    "16:9": (1200, 628),
}

# ---------- UI Components ----------

CTA_BUTTON = {
    "shape": "pill",
    "bg": COLORS["cta_bg"],
    "text_color": "#FFFFFF",
    "padding_px": (18, 40),
    "width_ratio": 0.65,  # % of canvas width
}

PRICE_BADGE = {
    "old_price_border": "#999999",
    "old_price_text": "#5A5A5A",
    "new_price_bg": "#000000",
    "new_price_text": "#FFFFFF",
    "gap_px": 10,
}

REVIEW_CARD = {
    "bg": "#FFFFFF",
    "border_radius": 16,
    "shadow_rgba": (0, 0, 0, 20),
    "shadow_offset": (0, 4),
    "shadow_blur": 16,
    "star_color": COLORS["star_gold"],
}

DASHED_LINE = {
    "dash_length_px": 3,
    "gap_px": 4,
    "stroke_width_px": 1.5,
    "color_on_light": "#333333",
    "color_on_dark": "#CCCCCC",
}

# ---------- Primary claims (for reference in prompts) ----------

PRIMARY_CLAIMS = [
    "Ancient Strength. Modern Convenience.",
    "No added sugar. Sweetened naturally with chicory root.",
    "Upgrade from messy, bitter resin to tasty, chewable gummies.",
    "2.5× Better Absorption compared to regular shilajit resin.",
    "Just 2 gummies a day. No bitterness. Easy to stay consistent.",
    "When your energy hits 0% — Recharge Smarter.",
    "Not just one batch. Every batch.",
    "Good-bye sugar spikes. Hello clean sweetness.",
]

ATTRIBUTE_CHIPS = [
    "No Added Sugar",
    "100% Natural",
    "Clinically Tested",
    "Superior Absorption",
    "Potent Fulvic Acid",
    "Gluten Free",
    "100% Vegan",
]

# ---------- Do's and Don'ts (short, injected into prompts) ----------

DOS = [
    "Use real ingredient photography",
    "Maximum 1 hero message per static",
    "Maintain consistent jar presentation",
    "Match palette to message: warm beige for ingredient/lifestyle, cool grey/white for clinical",
    "Keep CTA action-oriented",
]

DONTS = [
    "No purple, neon, or off-brand colors",
    "No stock photo humans (unless real Indian lifestyle)",
    "Max 3 claims in one static",
    "Never mix warm and cool backgrounds in one layout",
    "No artificial-looking gummies",
    "No serif headlines — sans-serif throughout",
]

# ---------- Template registry ----------

TEMPLATES = {
    "A": "Ingredient Spotlight (Flatlay)",
    "B": "Ingredient Close-Up (Hero Ingredient)",
    "C": "Benefit / Pain Point",
    "D": "Performance / Aspirational (Lifestyle)",
    "E": "Comparison / Upgrade",
    "F": "Social Proof (Reviews)",
    "G": "Price / Promotion",
    "H": "Quality / Testing Proof",
    "I": "Usage Instruction",
    "J": "Problem Awareness (Emotional)",
}

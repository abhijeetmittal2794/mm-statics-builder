"""Pydantic contracts between agents. Each agent consumes one model and returns another."""
from __future__ import annotations

from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field


# ---------- Inputs ----------

class CopyDeck(BaseModel):
    """Copies provided by the category person — never generated, always typeset verbatim."""
    headline: str = Field(..., description="Primary hook. Max 2 lines when rendered.")
    subhead: Optional[str] = None
    claim_bullets: list[str] = Field(default_factory=list, description="Short claims, max 3.")
    cta: Optional[str] = Field(None, description="e.g., 'Shop Now'")
    bottom_strip: list[str] = Field(
        default_factory=list,
        description="Attributes for the | separated footer strip, max 3.",
    )
    legal: Optional[str] = None
    tone_tag: Literal["awareness", "consideration", "decision", "conversion"] = "consideration"


class ReferenceBBox(BaseModel):
    """Normalized bounding box — fractions of canvas width/height.
    Reusable across any canvas size. Missing = element absent in reference."""
    x: float
    y: float
    w: float
    h: float

    def to_pixels(self, canvas_w: int, canvas_h: int) -> tuple[int, int, int, int]:
        x0 = int(self.x * canvas_w)
        y0 = int(self.y * canvas_h)
        x1 = int((self.x + self.w) * canvas_w)
        y1 = int((self.y + self.h) * canvas_h)
        return (x0, y0, x1, y1)


class ReferenceLayout(BaseModel):
    """Structure extracted from a competitor / inspiration static."""
    product: Optional[ReferenceBBox] = None
    headline: Optional[ReferenceBBox] = None
    subhead: Optional[ReferenceBBox] = None
    bottom_strip: Optional[ReferenceBBox] = None
    logo_position: Literal["top-left", "top-right", "bottom-left", "bottom-right"] = "top-left"
    palette_hex: list[str] = Field(default_factory=list)
    mood: str = ""
    notes: str = ""


class BuildInput(BaseModel):
    """The raw input the orchestrator receives."""
    reference_static_path: Optional[str] = Field(
        None, description="Path to a reference static to draw structural inspiration from."
    )
    product_image_path: str = Field(..., description="Path to the product photo (jar / gummy).")
    ingredients: list[str] = Field(
        default_factory=list,
        description="Ingredient keywords to feature (e.g., ['shilajit', 'ashwagandha']). Resolved to props at runtime.",
    )
    prop_image_paths: list[str] = Field(
        default_factory=list, description="Optional ingredient/prop photos."
    )
    copy_deck: CopyDeck
    format: Literal["1:1", "4:5", "9:16", "16:9"] = "4:5"
    template_hint: Optional[str] = Field(
        None,
        description="Optional: force a specific template (A-J). If None, Brand Translator picks.",
    )


# ---------- Agent 1: Brief Parser ----------

class LayoutZone(BaseModel):
    name: str
    purpose: str  # "headline", "product", "prop", "cta", "bottom_strip", etc.
    priority: int  # 1 = highest


class ParsedBrief(BaseModel):
    """Output of Brief Parser: the category person's intent, structured."""
    claim_type: Literal[
        "ingredient", "benefit", "problem", "comparison",
        "social_proof", "price", "testing", "usage", "absorption"
    ]
    audience_hook: str = Field(..., description="What emotional/rational hook is this static leading with?")
    reference_mood_keywords: list[str] = Field(default_factory=list)
    layout_zones: list[LayoutZone]
    has_human_figure: bool = False
    notes: str = ""


# ---------- Agent 2: Brand Translator ----------

class BrandSpec(BaseModel):
    """MM-adapted creative brief."""
    chosen_template: Literal["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
    background_mood: Literal[
        "warm_beige", "cool_light_grey", "dark_moody", "pure_white", "mountain_sky"
    ]
    primary_palette_hex: list[str]
    typography_notes: str
    composition_intent: str
    brand_guardrails_applied: list[str]


# ---------- Agent 3: Creative Director ----------

class ConceptCard(BaseModel):
    """One creative direction. Creative Director emits 2-3 of these."""
    concept_name: str
    scene_description: str = Field(
        ..., description="What does the viewer see? Describe atmosphere, not product details."
    )
    metaphor: Optional[str] = None
    product_placement: str  # "center-left tilted 10°", etc.
    prop_placement: Optional[str] = None
    negative_space_map: str = Field(
        ..., description="Where is whitespace reserved for copy?"
    )
    lighting_direction: str  # "soft front-right, warm cream fill"
    expected_palette_hex: list[str]


# ---------- Agent 4: Casting Director (stub for V2) ----------

class CastingSpec(BaseModel):
    """Populated only if ParsedBrief.has_human_figure == True."""
    tier: Literal["hero", "supporting", "ambient", "none"] = "none"
    ethnicity: str = "Indian"
    age_band: str = "25-40"
    wardrobe: str = ""
    pose: str = ""
    crop_strategy: str = ""
    skin_notes: str = ""
    negative_prompts: list[str] = Field(default_factory=list)
    use_real_reference_image: Optional[str] = None


# ---------- Agent 5: Scene Generator ----------

class SceneArtifact(BaseModel):
    scene_image_path: str
    placeholder_mask_path: Optional[str] = None
    prompt_used: str
    seed: Optional[int] = None


# ---------- Agent 5b: Scene Integrator (Nano Banana Pro edit-mode) ----------

class IntegrationArtifact(BaseModel):
    """Output of the Scene Integrator — backdrop + product + props harmonized."""
    integrated_image_path: str
    product_bbox_xyxy: tuple[int, int, int, int] = Field(
        ..., description="Where the product ended up in the integrated image."
    )
    prop_bboxes: list[tuple[int, int, int, int]] = Field(default_factory=list)
    prompt_used: str
    drift_score: Optional[float] = Field(
        None, description="Label-integrity drift score (lower is better). None if not measured."
    )
    passed_integrity_check: bool = True
    used_fallback: bool = Field(
        False,
        description="True if integrity check failed and we fell back to alpha composite.",
    )


# ---------- Agent 5c: Product Restamp ----------

class RestampArtifact(BaseModel):
    """Original product cutout alpha-composited on top of the integrated image.
    The integrator's shadows and lighting are preserved; label is guaranteed original."""
    restamped_image_path: str
    detected_bbox: tuple[int, int, int, int]
    detection_method: Literal["diff", "vision_llm", "hardcoded_fallback"]


# ---------- Agent 5d: Design Pass (NBP typography) ----------

class DesignedArtifact(BaseModel):
    """Typography rendered by Nano Banana Pro over the restamped image.
    If typography_passed is False, orchestrator falls back to code typography
    via the Compositor."""
    designed_image_path: str
    typography_passed: bool
    missing_or_wrong: list[str] = Field(default_factory=list)
    notes: str = ""


# ---------- Agent 6: Compositor (code, not LLM) ----------

class CompositedStatic(BaseModel):
    output_path: str
    width: int
    height: int
    template_used: str
    product_bbox_xyxy: tuple[int, int, int, int]


# ---------- Agent 7: QA Reviewer ----------

class QACheck(BaseModel):
    name: str
    passed: bool
    severity: Literal["blocker", "major", "minor"] = "minor"
    note: str = ""


class QAReport(BaseModel):
    overall_pass: bool
    score: float  # 0–1
    checks: list[QACheck]
    critiques_for_retry: list[str] = Field(default_factory=list)
    target_agent_for_retry: Optional[Literal[
        "creative_director", "casting_director", "scene_generator", "compositor"
    ]] = None


# ---------- Final Pipeline Artifact ----------

class PipelineRun(BaseModel):
    run_id: str
    input: BuildInput
    brief: Optional[ParsedBrief] = None
    reference_layout: Optional[ReferenceLayout] = None
    brand: Optional[BrandSpec] = None
    concepts: list[ConceptCard] = Field(default_factory=list)
    chosen_concept_index: Optional[int] = None
    casting: Optional[CastingSpec] = None
    scene: Optional[SceneArtifact] = None
    integration: Optional[IntegrationArtifact] = None
    restamp: Optional[RestampArtifact] = None
    designed: Optional[DesignedArtifact] = None
    composited: Optional[CompositedStatic] = None
    qa: Optional[QAReport] = None
    retry_count: int = 0
    final_path: Optional[str] = None

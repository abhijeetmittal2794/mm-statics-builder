"""Orchestrator — runs the full pipeline with retry loops.

Flow:
  Brief Parser
    → Brand Translator
    → Creative Director (3 concepts)
    → Casting Director (if human)
    → Scene Generator (backdrop only)
    → Scene Integrator (jar placed, lighting harmonized, shadow grounded)
    → Product Restamp (original jar pixels — label guaranteed)
    → Design Pass (NBP renders typography over the restamped image)
    → Typography Verifier (Claude vision checks text verbatim)
    → Compositor (picks designed image if verified, else code typography fallback)
    → QA Reviewer (code checks + vision judgment)

Retry routing:
  - QA "scene_generator"  → regenerate backdrop, re-integrate, restamp, design, composite
  - QA "compositor"       → re-integrate, restamp, design, composite
  - QA "creative_director"→ move to next concept card
"""
from __future__ import annotations

import uuid
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from .agents import (
    brand_translator,
    brief_parser,
    casting_director,
    compositor,
    creative_director,
    design_pass,
    product_restamp,
    qa_reviewer,
    reference_parser,
    scene_generator,
    scene_integrator,
    typography_verifier,
)
from .editor.state import build_default_layout, save_layout
from .models import BuildInput, DesignedArtifact, PipelineRun
from .product.prep import prepare_cutout
from .product.registry import hero_silhouette

console = Console()

MAX_SCENE_RETRIES = 2
MAX_CREATIVE_RETRIES = 1


def run(inp: BuildInput) -> PipelineRun:
    run_id = uuid.uuid4().hex[:10]
    console.print(Panel.fit(f"[bold cyan]MM Statics Builder[/] — run [yellow]{run_id}[/]"))

    pr = PipelineRun(run_id=run_id, input=inp)

    # 0. Reference Parser (optional — only if a reference static was provided)
    if inp.reference_static_path and Path(inp.reference_static_path).exists():
        console.print("[0] Reference Parser…")
        try:
            pr.reference_layout = reference_parser.run(Path(inp.reference_static_path))
            console.print(
                f"    extracted layout: product={_has(pr.reference_layout.product)}, "
                f"headline={_has(pr.reference_layout.headline)}, "
                f"subhead={_has(pr.reference_layout.subhead)}, "
                f"strip={_has(pr.reference_layout.bottom_strip)}"
            )
        except Exception as e:
            console.print(f"    ⚠ reference parse failed: {e} — continuing without")
            pr.reference_layout = None

    # 1. Brief Parser
    console.print("[1/10] Brief Parser…")
    pr.brief = brief_parser.run(inp)
    console.print(f"    claim_type={pr.brief.claim_type}, has_human={pr.brief.has_human_figure}")

    # 2. Brand Translator
    console.print("[2/10] Brand Translator…")
    pr.brand = brand_translator.run(inp, pr.brief)
    console.print(f"    template={pr.brand.chosen_template}, bg={pr.brand.background_mood}")

    # 3. Creative Director
    console.print("[3/10] Creative Director…")
    pr.concepts = creative_director.run(pr.brief, pr.brand)
    console.print(f"    produced {len(pr.concepts)} concepts")

    for creative_attempt in range(MAX_CREATIVE_RETRIES + 1):
        concept_idx = min(creative_attempt, len(pr.concepts) - 1)
        concept = pr.concepts[concept_idx]
        pr.chosen_concept_index = concept_idx
        console.print(f"  → trying concept #{concept_idx}: [italic]{concept.concept_name}[/]")

        # 4. Casting Director
        console.print("[4/10] Casting Director…")
        pr.casting = casting_director.run(pr.brief, concept)
        console.print(f"    tier={pr.casting.tier}")

        scene_attempt = 0
        while scene_attempt <= MAX_SCENE_RETRIES:
            # 5. Scene Generator
            console.print(f"[5/10] Scene Generator (attempt {scene_attempt + 1})…")
            pr.scene = scene_generator.run(
                inp=inp, brief=pr.brief, brand=pr.brand, concept=concept, casting=pr.casting
            )
            console.print(f"    backdrop: {pr.scene.scene_image_path}")

            # 6. Scene Integrator
            console.print("[6/10] Scene Integrator…")
            try:
                pr.integration = scene_integrator.run(
                    scene_path=Path(pr.scene.scene_image_path),
                    brief=pr.brief,
                    brand=pr.brand,
                    concept=concept,
                    casting=pr.casting,
                    aspect_ratio=inp.format,
                )
                console.print(f"    integrated: {pr.integration.integrated_image_path}")
            except Exception as e:
                console.print(f"    ⚠ integrator failed: {e} — will fall back to alpha composite")
                pr.integration = None
                pr.restamp = None
                pr.designed = None

            # 7. Product Restamp
            if pr.integration:
                console.print("[7/10] Product Restamp…")
                try:
                    pr.restamp = product_restamp.run(
                        scene_path=Path(pr.scene.scene_image_path),
                        integrated_path=Path(pr.integration.integrated_image_path),
                        product_cutout_path=prepare_cutout(hero_silhouette()),
                        fallback_bbox=pr.integration.product_bbox_xyxy,
                    )
                    console.print(
                        f"    restamped: {pr.restamp.restamped_image_path} "
                        f"(bbox via {pr.restamp.detection_method})"
                    )
                except Exception as e:
                    console.print(f"    ⚠ restamp failed: {e} — will use code typography path")
                    pr.restamp = None

            # 8. Design Pass (NBP typography) + Typography Verification
            pr.designed = None
            if pr.restamp:
                console.print("[8/10] Design Pass (NBP typography)…")
                try:
                    designed_path = design_pass.run(
                        inp=inp,
                        brand=pr.brand,
                        restamped_path=Path(pr.restamp.restamped_image_path),
                        aspect_ratio=inp.format,
                    )
                    console.print(f"    designed: {designed_path}")

                    console.print("    verifying typography…")
                    report = typography_verifier.run(
                        designed_image_path=designed_path,
                        copy=inp.copy_deck,
                    )
                    pr.designed = DesignedArtifact(
                        designed_image_path=str(designed_path),
                        typography_passed=report.passed,
                        missing_or_wrong=report.missing_or_wrong,
                        notes=report.notes,
                    )
                    if report.passed:
                        console.print("    [green]✓ typography verified clean[/]")
                    else:
                        console.print(
                            f"    [yellow]⚠ typography drift[/] — falling back to code typography"
                        )
                        for item in report.missing_or_wrong:
                            console.print(f"      missing/wrong: {item}")
                except Exception as e:
                    console.print(f"    ⚠ design pass failed: {e} — using code typography")
                    pr.designed = None

            # 9. Compositor
            console.print("[9/10] Compositor…")
            pr.composited = compositor.run(
                inp=inp,
                brief=pr.brief,
                brand=pr.brand,
                scene=pr.scene,
                restamp=pr.restamp,
                designed=pr.designed,
            )
            console.print(f"    final: {pr.composited.output_path}")

            # 10. QA (non-fatal — the static is already on disk)
            console.print("[10/10] QA Reviewer…")
            try:
                pr.qa = qa_reviewer.run(
                    final=pr.composited,
                    product_reference_path=Path(inp.product_image_path),
                    brief=pr.brief,
                    brand=pr.brand,
                )
                console.print(
                    f"    QA score={pr.qa.score:.2f} pass={pr.qa.overall_pass} "
                    f"retry_target={pr.qa.target_agent_for_retry}"
                )
            except Exception as e:
                console.print(f"    ⚠ QA skipped: {e}")
                console.print("    [dim]Static is on disk; editor layout saved.[/]")
                pr.final_path = pr.composited.output_path
                _persist_editor_layout(pr)
                console.print(Panel.fit(
                    f"[bold green]✓ Static ready (QA skipped)[/]\n{pr.final_path}\n\n"
                    f"[dim]Edit:[/] python cli.py edit --run-id {pr.run_id}"
                ))
                return pr
            pr.retry_count = scene_attempt + creative_attempt

            if pr.qa.overall_pass:
                pr.final_path = pr.composited.output_path
                _persist_editor_layout(pr)
                console.print(Panel.fit(
                    f"[bold green]✓ Passed QA[/]\n{pr.final_path}\n\n"
                    f"[dim]Edit:[/] python cli.py edit --run-id {pr.run_id}"
                ))
                return pr

            for critique in pr.qa.critiques_for_retry:
                console.print(f"    ⚠ {critique}")

            target = pr.qa.target_agent_for_retry
            if target in ("scene_generator", "compositor") and scene_attempt < MAX_SCENE_RETRIES:
                scene_attempt += 1
                continue
            break

    pr.final_path = pr.composited.output_path if pr.composited else None
    _persist_editor_layout(pr)
    console.print(Panel.fit(
        f"[bold yellow]⚠ Exhausted retries[/]\n{pr.final_path}\n\n"
        f"[dim]Edit:[/] python cli.py edit --run-id {pr.run_id}"
    ))
    return pr


def _has(x) -> str:
    return "✓" if x is not None else "—"


def _persist_editor_layout(pr: PipelineRun) -> None:
    """Write the default EditorState for this run so the editor can load it."""
    if not (pr.scene and pr.brand):
        return
    try:
        state = build_default_layout(pr)
        save_layout(state)
    except Exception as e:
        console.print(f"[dim]Could not persist editor layout: {e}[/]")

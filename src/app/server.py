"""FastAPI backend for the Statics Builder web app.

Endpoints:
  GET  /              → single-page app
  GET  /api/config    → form dropdowns (ingredients, templates, formats, claims)
  POST /api/generate  → start multi-variant generation (4 variants, background task)
  GET  /api/status/X  → poll generation progress
  POST /api/rate      → rate a variant; >= 8 saves to approved
  GET  /api/approved  → list approved outputs
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from fastapi import BackgroundTasks, FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ..brand.tokens import ATTRIBUTE_CHIPS, PRIMARY_CLAIMS, TEMPLATES
from ..models import BuildInput, CopyDeck
from ..pipeline import run_variant
from ..product.props import PROPS
from ..product.registry import hero_silhouette
from .memory import get_approved_refs, list_approved, save_approved

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
UPLOADS_DIR = OUTPUTS_DIR / "uploads"
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="MM Statics Builder")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/assets", StaticFiles(directory=PROJECT_ROOT), name="assets")

NUM_VARIANTS = 4


# ---------- In-memory run tracking ----------

@dataclass
class VariantStatus:
    index: int
    status: Literal["pending", "running", "done", "error"] = "pending"
    path: str | None = None
    error: str | None = None


@dataclass
class RunStatus:
    run_id: str
    total: int
    params: dict = field(default_factory=dict)
    variants: list[VariantStatus] = field(default_factory=list)


_RUNS: dict[str, RunStatus] = {}


# ---------- Endpoints ----------

@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/config")
def api_config():
    return {
        "ingredients": [
            {"keyword": p.keyword, "display_name": p.display_name, "description": p.description}
            for p in PROPS if p.image_path.exists()
        ],
        "templates": TEMPLATES,
        "formats": ["1:1", "4:5", "9:16", "16:9"],
        "attribute_chips": ATTRIBUTE_CHIPS,
        "primary_claims": PRIMARY_CLAIMS,
    }


@app.post("/api/generate")
async def api_generate(
    background_tasks: BackgroundTasks,
    headline: str = Form(...),
    subhead: str = Form(""),
    cta: str = Form("Shop Now"),
    bottom_strip_1: str = Form("No Added Sugar"),
    bottom_strip_2: str = Form("100% Natural"),
    bottom_strip_3: str = Form("Clinically Tested"),
    ingredients: str = Form("[]"),
    format: str = Form("4:5"),
    template_hint: str = Form(""),
    include_human: bool = Form(False),
    reference_image: UploadFile | None = File(None),
):
    run_id = uuid.uuid4().hex[:10]
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    ref_path: str | None = None
    if reference_image and reference_image.filename:
        ext = Path(reference_image.filename).suffix or ".png"
        ref_file = UPLOADS_DIR / f"ref_{run_id}{ext}"
        ref_file.write_bytes(await reference_image.read())
        ref_path = str(ref_file)

    strip = [s for s in [bottom_strip_1, bottom_strip_2, bottom_strip_3] if s.strip()]
    ing_list = json.loads(ingredients) if ingredients else []

    inp = BuildInput(
        reference_static_path=ref_path,
        product_image_path=str(hero_silhouette()),
        prop_image_paths=[],
        ingredients=ing_list,
        copy_deck=CopyDeck(
            headline=headline,
            subhead=subhead or None,
            cta=cta or None,
            bottom_strip=strip,
            tone_tag="consideration",
        ),
        format=format,
        template_hint=template_hint or None,
    )

    params = {
        "headline": headline,
        "subhead": subhead,
        "cta": cta,
        "bottom_strip": strip,
        "ingredients": ing_list,
        "format": format,
        "template_hint": template_hint,
        "include_human": include_human,
    }

    rs = RunStatus(
        run_id=run_id,
        total=NUM_VARIANTS,
        params=params,
        variants=[VariantStatus(index=i) for i in range(NUM_VARIANTS)],
    )
    _RUNS[run_id] = rs

    background_tasks.add_task(_generate_all, run_id, inp, include_human)
    return {"run_id": run_id, "variant_count": NUM_VARIANTS}


def _generate_all(run_id: str, inp: BuildInput, include_human: bool) -> None:
    rs = _RUNS[run_id]
    approved_refs = get_approved_refs(max_count=3)
    for i in range(rs.total):
        rs.variants[i].status = "running"
        try:
            path = run_variant(
                inp=inp,
                variant_index=i,
                run_id=run_id,
                extra_style_refs=approved_refs,
                force_human=include_human if include_human else None,
            )
            rs.variants[i].path = path
            rs.variants[i].status = "done"
        except Exception as e:
            rs.variants[i].error = str(e)
            rs.variants[i].status = "error"


@app.get("/api/status/{run_id}")
def api_status(run_id: str):
    rs = _RUNS.get(run_id)
    if not rs:
        return JSONResponse({"error": "unknown run_id"}, 404)

    def _url(path: str | None) -> str | None:
        if not path:
            return None
        p = Path(path)
        try:
            rel = p.relative_to(PROJECT_ROOT)
            return "/assets/" + rel.as_posix()
        except ValueError:
            return None

    return {
        "run_id": rs.run_id,
        "total": rs.total,
        "completed": sum(1 for v in rs.variants if v.status in ("done", "error")),
        "params": rs.params,
        "variants": [
            {
                "index": v.index,
                "status": v.status,
                "url": _url(v.path),
                "error": v.error,
            }
            for v in rs.variants
        ],
    }


@app.post("/api/rate")
async def api_rate(body: dict):
    run_id = body.get("run_id")
    idx = body.get("variant_index")
    rating = body.get("rating", 0)

    rs = _RUNS.get(run_id)
    if not rs or idx is None or idx >= len(rs.variants):
        return JSONResponse({"error": "invalid"}, 400)

    v = rs.variants[idx]
    saved = False
    approved_path = None

    if rating >= 8 and v.path:
        meta = {**rs.params, "rating": rating, "variant_index": idx, "run_id": run_id}
        dest = save_approved(v.path, meta)
        saved = True
        approved_path = str(dest)

    return {"saved": saved, "approved_path": approved_path, "rating": rating}


@app.get("/api/approved")
def api_approved():
    return list_approved()

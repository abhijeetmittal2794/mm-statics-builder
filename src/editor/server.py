"""FastAPI server for the browser editor.

Endpoints:
  GET  /                 → editor HTML
  GET  /api/layout       → current EditorState JSON (with file paths rewritten as URLs)
  POST /api/render       → accept an EditorState, render PNG, return output path
  /static/*              → editor assets (CSS/JS)
  /assets/*              → project files (outputs, fonts) served for the frontend
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .renderer import render
from .state import EditorState, load_layout

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="MM Statics Editor")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/assets", StaticFiles(directory=PROJECT_ROOT), name="assets")

# run_id is set by the CLI before the server starts
_CURRENT_RUN_ID: str | None = None


def set_run_id(run_id: str) -> None:
    global _CURRENT_RUN_ID
    _CURRENT_RUN_ID = run_id


def _url_for(path: str) -> str:
    """Convert an absolute filesystem path into a URL the frontend can fetch."""
    p = Path(path)
    if not p.is_absolute():
        p = (PROJECT_ROOT / p).resolve()
    try:
        rel = p.relative_to(PROJECT_ROOT)
        return "/assets/" + rel.as_posix()
    except ValueError:
        return str(p)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/layout")
def api_layout() -> JSONResponse:
    if not _CURRENT_RUN_ID:
        raise HTTPException(400, "No run_id configured on server")
    state = load_layout(_CURRENT_RUN_ID)
    data = state.model_dump()
    # Rewrite filesystem paths to URLs the browser can fetch
    data["backdrop_url"] = _url_for(state.backdrop_path)
    data["product"]["cutout_url"] = _url_for(state.product.cutout_path)
    return JSONResponse(data)


@app.post("/api/render")
async def api_render(body: dict) -> JSONResponse:
    # Strip the URL fields — renderer only knows about filesystem paths
    body.pop("backdrop_url", None)
    if "product" in body:
        body["product"].pop("cutout_url", None)
    state = EditorState.model_validate(body)
    out_path = render(state)
    return JSONResponse({
        "output_path": str(out_path),
        "output_url": _url_for(str(out_path)),
    })

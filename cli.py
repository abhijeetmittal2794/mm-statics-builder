"""Command-line entry point for the statics builder.

Usage:
    python cli.py build --brief briefs/example.json
    python cli.py build --brief briefs/example.json --format 1:1
    python cli.py demo   # runs the bundled example brief end-to-end
"""
from __future__ import annotations

import json
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console

from src.models import BuildInput, CopyDeck
from src.pipeline import run as run_pipeline

console = Console()


@click.group()
def cli():
    """Man Matters Statics Builder."""
    load_dotenv()


@cli.command()
@click.option("--port", default=8080, help="Local port.")
@click.option("--no-browser", is_flag=True)
def app(port: int, no_browser: bool):
    """Launch the Statics Builder web app."""
    import webbrowser
    import uvicorn
    from src.app.server import app as web_app
    url = f"http://127.0.0.1:{port}"
    console.print(f"[bold]Statics Builder:[/] [cyan]{url}[/]")
    if not no_browser:
        webbrowser.open(url)
    uvicorn.run(web_app, host="127.0.0.1", port=port, log_level="info")


@cli.command()
@click.option("--brief", "brief_path", type=click.Path(exists=True), required=True,
              help="Path to a brief JSON file.")
@click.option("--format", "fmt", default=None, help="Override format (1:1, 4:5, 9:16, 16:9).")
def build(brief_path: str, fmt: str | None):
    """Build a single static from a brief file."""
    data = json.loads(Path(brief_path).read_text())
    if fmt:
        data["format"] = fmt
    inp = BuildInput.model_validate(data)
    out = run_pipeline(inp)
    console.print(f"\n[bold]Final:[/] {out}")


@cli.command()
def models():
    """List image-capable Gemini models your GOOGLE_API_KEY can access."""
    from src.clients.nano_banana import list_image_models
    ids = list_image_models()
    if not ids:
        console.print("[yellow]No image models found for this key.[/]")
        return
    console.print("[bold]Image-capable models available to your key:[/]")
    for m in ids:
        console.print(f"  - {m}")
    console.print(
        "\nSet the best one as NANO_BANANA_MODEL in your .env.\n"
        "Pro tier (best quality) is 'gemini-3-pro-image-preview'; "
        "fallback is 'gemini-2.5-flash-image-preview'."
    )


@cli.command()
@click.option("--run-id", default=None,
              help="Pipeline run_id. Omit to use the most recent. Use 'list' to see all.")
@click.option("--port", default=8765, help="Local port for the editor server.")
@click.option("--no-browser", is_flag=True, help="Do not open the browser automatically.")
def edit(run_id: str | None, port: int, no_browser: bool):
    """Launch the visual editor for a pipeline run's layout."""
    import webbrowser
    from pathlib import Path

    import uvicorn

    from src.editor.server import app, set_run_id

    layouts_dir = Path(__file__).parent / "outputs" / "layouts"
    available = sorted(
        layouts_dir.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    ) if layouts_dir.exists() else []

    if run_id == "list":
        if not available:
            console.print("[yellow]No saved layouts. Run 'python cli.py demo' first.[/]")
        else:
            console.print("[bold]Saved layouts (newest first):[/]")
            for p in available:
                console.print(f"  {p.stem}  [dim]{p.stat().st_mtime:.0f}[/]")
        return

    if not available:
        console.print(
            "[red]No saved layouts in outputs/layouts/.[/]\n"
            "Run [cyan]python cli.py demo[/] first to generate one."
        )
        return

    resolved = run_id
    if resolved is None:
        resolved = available[0].stem
        console.print(f"[dim]No --run-id given; using most recent: {resolved}[/]")
    elif not (layouts_dir / f"{resolved}.json").exists():
        console.print(f"[red]No layout for run_id '{resolved}'.[/]")
        console.print("[bold]Available:[/]")
        for p in available[:10]:
            console.print(f"  {p.stem}")
        return

    set_run_id(resolved)
    url = f"http://127.0.0.1:{port}"
    console.print(f"[bold]Editor:[/] [cyan]{url}[/]  (run_id: {resolved})")
    if not no_browser:
        webbrowser.open(url)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


@cli.command()
def demo():
    """Run the bundled example brief."""
    project = Path(__file__).parent
    example = project / "briefs" / "example.json"
    if not example.exists():
        console.print(f"[red]Example brief not found at {example}[/]")
        raise SystemExit(1)
    data = json.loads(example.read_text())
    inp = BuildInput.model_validate(data)
    out = run_pipeline(inp)
    console.print(f"\n[bold]Final:[/] {out}")


if __name__ == "__main__":
    cli()

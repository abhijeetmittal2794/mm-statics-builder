# MM Shilajit Statics Builder

A multi-agent pipeline that converts a reference brief + product photo + copy deck into an on-brand Man Matters Shilajit Gummies static ad — without distorting the product label, hallucinating ingredients, or garbling typography.

## Design principles

1. **The image model generates scene only.** Never the product, never copy, never the logo.
2. **The product is composited from real pixels.** Background-removed cutout, guaranteed label integrity.
3. **Typography is typeset in code.** Pillow + real font files. The model cannot garble what it doesn't render.
4. **Every agent has one job.** Clean Pydantic contracts between them.

## Agent roster

| # | Agent | Kind | Role |
|---|---|---|---|
| 1 | Brief Parser | Claude | Structures the category person's intent |
| 2 | Brand Translator | Claude + vision | Maps to MM visual language, picks template |
| 3 | Creative Director | Claude | Emits 3 concept cards (the creative layer) |
| 4 | Casting Director | Claude | Spec humans (if any) — hero/supporting/ambient tier |
| 5 | Scene Generator | Nano Banana Pro | Renders scene backdrop only |
| 6 | Compositor | Pure Python (Pillow) | Places product cutout + typesets copy |
| 7 | QA Reviewer | Claude + vision | Checks label, palette, typography, composition |

Orchestrator (`src/orchestrator.py`) sequences them with retry loops.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in ANTHROPIC_API_KEY and GOOGLE_API_KEY
```

Drop font files into `src/fonts/` (see `src/brand/tokens.py::FONT_ROLES`). Minimum: an Inter or similar bold sans and a regular sans.

## Run

```bash
python cli.py demo                    # run bundled example brief
python cli.py build --brief briefs/example.json --format 4:5
```

Outputs land in `outputs/statics/`. Scenes land in `outputs/scenes/`. Product cutouts cached in `outputs/.cutout_cache/`.

## V1 scope

- Template B (Ingredient Close-Up) fully wired end-to-end
- Other 9 templates: stubbed in `src/layouts/`, add one file per template to light them up
- Casting Director: wired but not exercised on Template B (no humans)

## V2 roadmap

- Templates A, C, D, E, F, G, H, I, J
- Casting Director activation with shot-library references for hero shots
- Multi-variant generation (run all 3 concepts, return top 3 by QA score)
- Web UI for brief intake

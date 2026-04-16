"""Agent 5e: Typography Verifier.

After NBP's Design Pass adds typography, this agent uses Claude vision to confirm
that every expected copy-deck phrase appears verbatim in the designed image —
correct spelling, correct punctuation, crisp rendering.

One letter wrong = fail. Returns the list of problem phrases so the orchestrator
can fall back to code typography cleanly.
"""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from ..clients.anthropic_client import call_claude
from ..models import CopyDeck
from ._common import parse_model


class TypographyReport(BaseModel):
    passed: bool
    missing_or_wrong: list[str]
    notes: str = ""


_SYSTEM = """You verify that typography in an advertising static matches a provided copy deck verbatim. You are strict — even a single wrong letter, dropped word, or blurred phrase is a failure. Return JSON only, no prose."""


def run(*, designed_image_path: Path, copy: CopyDeck) -> TypographyReport:
    expected: list[str] = [copy.headline]
    if copy.subhead:
        expected.append(copy.subhead)
    if copy.bottom_strip:
        expected.extend(copy.bottom_strip)
    if copy.cta:
        expected.append(copy.cta)

    expected_block = "\n".join(f'  {i + 1}. "{e}"' for i, e in enumerate(expected))

    user_text = (
        "Verify the typography rendered in this advertising static against the copy deck.\n\n"
        "EXPECTED phrases (each must appear in the image verbatim — exact spelling, "
        "punctuation, capitalization, and word order):\n"
        f"{expected_block}\n\n"
        "Rules for passing:\n"
        "- Every expected phrase must appear in the image.\n"
        "- Each phrase must be crisp and readable (no blur, no warped letters).\n"
        "- No letter may be wrong, dropped, or substituted.\n"
        "- No extra copy/claims/taglines are invented.\n\n"
        "Return this exact JSON shape:\n"
        '{"passed": true|false, "missing_or_wrong": ["<phrase exactly as expected>"], "notes": "<brief>"}\n\n'
        "If everything matches, passed=true and missing_or_wrong=[]. Otherwise list "
        "each problem phrase exactly as it appears in the EXPECTED list (not as rendered)."
    )

    response = call_claude(
        system=_SYSTEM,
        user_text=user_text,
        image_paths=[designed_image_path],
        temperature=0.0,
        max_tokens=600,
    )
    return parse_model(response, TypographyReport)

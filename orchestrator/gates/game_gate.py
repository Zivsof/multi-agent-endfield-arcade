"""Deterministic game gate before Playwright QA (Step 8).

Plain Python file/content checks — no LLM, no browser. Catches missing files,
missing ``../common.css``, missing disclaimer marker, missing difficulty handling,
and classic Arknights TD lore smells that belong outside this Endfield arcade.

Called by ``test_game``:
  - first pass → ``check_game``
  - after ``relaunch_worker`` → ``regate`` (same checks; name signals repair path)

Fail fast so we do not burn Playwright / Gemini tokens on empty folders.
"""

from __future__ import annotations

import re
from pathlib import Path

from orchestrator.content.disclaimer import GATE_MARKER

GAME_FILES = ("game.html", "game.css", "game.js")
_DIFFICULTY_HINT = re.compile(
    r"difficulty|beginner|veteran|location\.search|URLSearchParams",
    re.IGNORECASE,
)
_TOGGLE_HINT = re.compile(r"beginner|veteran", re.IGNORECASE)
# Classic Arknights TD / Rhodes Island smells — Endfield arcade should not quiz these.
_AK1_SMELL = re.compile(
    r"\b(Amiya|Exusiai|SilverAsh|Silver Ash|Texas the Omertosa|Ch'?en|"
    r"Rhodes Island|Deployment Points?\b|DP cost|redeploy timer|tile grid|"
    r"tower[- ]defence|tower[- ]defense)\b",
    re.IGNORECASE,
)


def check_game(folder: Path) -> dict:
    """Return ``{ok: bool, failures: list[str]}`` for one ``site/{slug}/`` folder.

    Failure codes (examples): ``missing_or_empty:game.js``, ``missing_common_css_link``,
    ``missing_disclaimer_marker``, ``missing_difficulty_handling``,
    ``classic_arknights_lore_smell``.
    """
    failures: list[str] = []
    for name in GAME_FILES:
        path = folder / name
        if not path.exists() or path.stat().st_size == 0:
            failures.append(f"missing_or_empty:{name}")

    html_path = folder / "game.html"
    js_path = folder / "game.js"
    html = html_path.read_text(encoding="utf-8") if html_path.exists() else ""
    js = js_path.read_text(encoding="utf-8") if js_path.exists() else ""
    combined = html + "\n" + js

    if 'href="../common.css"' not in html and "href='../common.css'" not in html:
        failures.append("missing_common_css_link")
    # GATE_MARKER is a stable substring of DISCLAIMER (see disclaimer.py).
    if GATE_MARKER not in html and GATE_MARKER not in combined:
        failures.append("missing_disclaimer_marker")
    if not _DIFFICULTY_HINT.search(combined):
        failures.append("missing_difficulty_handling")
    elif not _TOGGLE_HINT.search(combined):
        failures.append("missing_beginner_veteran_copy")
    if _AK1_SMELL.search(combined):
        failures.append("classic_arknights_lore_smell")

    return {"ok": not failures, "failures": failures}


def format_gate_failure(slug: str, result: dict) -> str:
    """One-line reason string for the orchestrator / relaunch_worker problem text."""
    fails = ", ".join(result.get("failures") or ["unknown"])
    return f"{slug}: GATE_FAIL. {fails}"


def regate(folder: Path) -> dict:
    """Re-run acceptance after a repair (same checks as ``check_game``)."""
    return check_game(folder)

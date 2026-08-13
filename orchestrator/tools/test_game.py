"""Step 8 — ADK tool ``test_game``: acceptance gate first, then Playwright QA.

Agent view: ``test_game(slug="strands")`` — which folder to judge. Returns a JSON
string the orchestrator can feed into ``relaunch_worker`` if broken.

Python view (order matters):
  1. Run deterministic ``game_gate.check_game`` (or ``regate`` after a repair).
  2. If gate fails → return broken / repaired_but_gate_failed **without** opening a browser.
  3. If gate passes → Playwright MCP QA agent plays ``file://…/game.html``.
  4. Store verdict on ``team.run_entries[slug]`` for the run report.

Statuses the orchestrator should understand:
  - ``works`` — gate ok + QA says it plays
  - ``broken`` — gate fail or QA says broken
  - ``unknown`` — browser/budget/timeout; **not** a pass (do not treat as WORKS)
  - ``repaired_but_gate_failed`` — already repaired once; gate still fails → skip QA
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

import config
from board import live as live_board
from orchestrator import report
from orchestrator.gates import game_gate
from qa import agent as qa_agent

if TYPE_CHECKING:
    from orchestrator.agent import Team

QA_TIMEOUT = config.QA_TIMEOUT_S


def make_test_game(team: "Team"):
    """Return the ``test_game`` tool bound to this run's ``Team``."""

    async def test_game(slug: str) -> str:
        """Gate then (if ok) play one finished game. Returns structured JSON-ish verdict.

        Args:
            slug: framework folder name, e.g. strands.
        """
        worker = team.by_slug.get(slug)
        folder = team.site_dir / slug
        if worker is None and not folder.is_dir():
            return f"No game in folder '{slug}'."

        # After relaunch_worker sets repaired=True, use regate (same checks; clear name for logs).
        repaired = bool(team.run_entries.setdefault(slug, report.empty_worker_entry(slug)).get("repaired"))
        gate = game_gate.regate(folder) if repaired else game_gate.check_game(folder)
        team.run_entries[slug]["gate"] = gate
        team.run_entries[slug]["built"] = team._built(slug)

        if not gate["ok"]:
            # Cheap fail: do not spend Playwright tokens on empty/broken files.
            text = game_gate.format_gate_failure(slug, gate)
            status = "repaired_but_gate_failed" if repaired else "broken"
            payload = {
                "slug": slug,
                "works": False,
                "status": status,
                "reason": text,
                "checks": gate["failures"],
            }
            team.run_entries[slug]["qa"] = payload
            if repaired:
                team.run_entries[slug]["repaired_but_gate_failed"] = True
            return json.dumps(payload)

        uri = (folder / "game.html").resolve().as_uri()
        colour = worker["colour"] if worker else "white"
        live_board.console.print(f"Playing {slug} to check it", style=colour)
        try:
            verdict = await asyncio.wait_for(
                qa_agent.judge_game(team.theme, team.objectives.get(slug, ""), uri),
                timeout=QA_TIMEOUT,
            )
        except Exception as exc:
            # Timeout or crash → unknown (orchestrator may still try one repair).
            payload = {
                "slug": slug,
                "works": False,
                "status": "unknown",
                "reason": f"QA error: {type(exc).__name__}",
                "checks": [],
            }
            team.run_entries[slug]["qa"] = payload
            return json.dumps(payload)
        if not verdict:
            payload = {
                "slug": slug,
                "works": False,
                "status": "unknown",
                "reason": "Browser unavailable; could not play.",
                "checks": [],
            }
            team.run_entries[slug]["qa"] = payload
            return json.dumps(payload)

        status = verdict.get("status") or ("works" if verdict.get("works") else "broken")
        reason = verdict.get("reason") or verdict.get("note") or ""
        payload = {
            "slug": slug,
            "works": bool(verdict.get("works")) and status == "works",
            "status": status,
            "reason": reason,
            "checks": verdict.get("checks") or [],
        }
        team.run_entries[slug]["qa"] = payload
        live_board.console.print(
            f"  {slug}: {status.upper()}. {reason}",
            style="green" if payload["works"] else "red",
        )
        return json.dumps(payload)

    return test_game

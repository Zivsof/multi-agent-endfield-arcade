"""Step 7 — ADK tool ``wait_for_team``: block until launched workers exit.

Agent view: call ``wait_for_team()`` with no args after ``launch_worker`` (often after
launching everyone). Returns a text status the orchestrator can read before
``test_game``.

Python view:
  1. Take ownership of ``team.pending`` (the list Step 5 filled with Popen handles).
  2. Show a Rich **live** board that refreshes from SQLite while children run.
  3. Poll until every process exits, or kill hung ones after ``WORKER_TIMEOUT_S``.
  4. Close log files; record exit_code / duration / built into ``run_entries``.
  5. Return ``team.status()`` (+ hung-slug names if any were killed).

Does **not** start workers or judge game quality — only waits (and maybe kills).
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

from rich.live import Live

import config
from board import live as live_board
from orchestrator.tools.launch import terminate

if TYPE_CHECKING:
    from orchestrator.agent import Team

WORKER_TIMEOUT = config.WORKER_TIMEOUT_S


def make_wait_for_team(team: "Team"):
    """Return the ``wait_for_team`` tool bound to this run's ``Team``."""

    async def wait_for_team() -> str:
        """Wait until every builder you started has finished. Returns team status."""
        # Drain pending so a second wait_for_team in the same run starts clean.
        # (After relaunch_worker, pending is filled again — wait again.)
        procs = team.pending
        team.pending = []
        if not procs:
            return team.status()
        started = time.monotonic()
        stopped = False
        hung: list[str] = []
        # Live() redraws the same terminal region ~8×/sec with the current board snapshot.
        with Live(live_board.render(team.registry), console=live_board.console, refresh_per_second=8) as live:
            # poll() is None ⇒ process still running; non-None ⇒ exit code.
            while any(p["proc"].poll() is None for p in procs):
                live.update(live_board.render(team.registry))
                if not stopped and time.monotonic() - started > WORKER_TIMEOUT:
                    for p in procs:
                        if p["proc"].poll() is None:
                            terminate(p["proc"])  # kill process group (see launch.terminate)
                            hung.append(p["slug"])
                    stopped = True  # only attempt kill once
                await asyncio.sleep(0.15)
            live.update(live_board.render(team.registry))
        for p in procs:
            try:
                p["log"].close()
            except Exception:
                pass
            code = p["proc"].poll()
            slug = p["slug"]
            dur = round(time.monotonic() - p["started"], 2)
            team.run_entries[slug]["exit_code"] = code
            team.run_entries[slug]["duration_s"] = dur
            team.run_entries[slug]["built"] = team._built(slug)
        msg = team.status()
        if hung:
            msg += f"\nHung workers stopped after timeout: {', '.join(hung)}"
        return msg

    return wait_for_team

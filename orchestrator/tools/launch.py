"""Step 5 — launch / terminate worker subprocesses + ADK ``launch_worker`` tool.

Agent view: ``launch_worker(framework, objective)`` — chooses *who* builds and *what*
topic. Returns immediately ("Launched…"); it does **not** wait for the game to finish
(that is Step 7 ``wait_for_team``).

Python view:
  1. Validate framework / no duplicate launch / distinct objectives.
  2. Maybe rewrite classic-Arknights-smelling objectives via lore.
  3. Format ``GAME_TASK`` and ``board.add_goal`` → SQLite row with full build brief.
  4. ``subprocess.Popen`` the worker with ``(goal_id, board_path)``.
  5. Tee stdout/stderr to ``site/logs/{slug}.log``; append to ``team.pending``.

The child process (Step 6) claims that goal, plans steps, and writes ``site/{slug}/game.*``.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

import config
from board import board as board_api
from orchestrator import catalog
from orchestrator.content import lore, prompts
from orchestrator.content.disclaimer import DISCLAIMER

if TYPE_CHECKING:
    from orchestrator.agent import Team


def launch(goal_id: int, worker: dict, board_path: Path, site_dir: Path) -> dict:
    """Start one worker subprocess and return a pending-entry dict for ``wait_for_team``.

    Returns ``{"slug", "proc", "log", "started"}`` where ``proc`` is the ``Popen`` handle
    and ``log`` is an open file handle for the tee'd log.
    """
    argv = catalog.launch_argv(worker, goal_id, board_path)
    # Run with cwd = worker's folder so relative imports (e.g. ``import board``) resolve.
    cwd = str((catalog.ROOT / worker["file"]).resolve().parent)
    # New process group on Unix so terminate() can kill the whole tree (MCP children too).
    group = {} if sys.platform == "win32" else {"start_new_session": True}
    logs_dir = site_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"{worker['slug']}.log"
    log_f = open(log_path, "w", encoding="utf-8")
    env = os.environ.copy()
    env["BOARD_PATH"] = str(board_path)
    env["WORKER_MODEL"] = config.WORKER_MODEL
    proc = subprocess.Popen(
        argv, stdout=log_f, stderr=subprocess.STDOUT, cwd=cwd, env=env, **group
    )
    return {"slug": worker["slug"], "proc": proc, "log": log_f, "started": time.monotonic()}


def terminate(proc: subprocess.Popen) -> None:
    """Best-effort kill of a hung worker process group (used by wait_for_team timeout)."""
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (ProcessLookupError, OSError):
        pass


def make_launch_worker(team: "Team"):
    """Return the ADK ``launch_worker`` tool bound to this run's ``Team``."""

    def launch_worker(framework: str, objective: str) -> str:
        """Start one framework's builder with an Endfield learning objective. Returns immediately.

        Args:
            framework: strands, pydantic, maf, agno, or mastra.
            objective: distinct Endfield topic for this builder.
        """
        worker = team.by_key.get(framework)
        if worker is None:
            return f"No builder named '{framework}'. Your team is: {', '.join(team.by_key)}."
        slug = worker["slug"]
        if slug in team.objectives:
            return f"{worker['name']} is already building on {team.objectives[slug]}."
        role = worker.get("default_role", "")
        # Prefer curriculum seed when the orchestrator drifts toward classic AK wording.
        objective = _prefer_endfield_objective(role, objective)
        norm = catalog.normalize_objective(objective)
        if norm in team._seen_objectives:
            return f"Objective '{objective}' is already assigned. Choose a distinct one."
        team._seen_objectives.add(norm)
        team.objectives[slug] = objective
        (team.site_dir / slug).mkdir(parents=True, exist_ok=True)
        # Full build brief the *worker* will read via show_todos — not a short CLI flag.
        task = prompts.GAME_TASK.format(
            objective=objective,
            slug=slug,
            role=role,
            disclaimer=DISCLAIMER,
            lore_block=prompts.LORE_BLOCK,
            design_block=prompts.DESIGN_BLOCK,
        )
        goal_id = board_api.add_goal(task)
        team.registry[goal_id] = {**worker, "objective": objective}
        entry = launch(goal_id, worker, team.board_path, team.site_dir)
        team.pending.append(entry)
        team.run_entries[slug].update(
            {
                "launched": True,
                "objective": objective,
                "role": role,
                "log": f"logs/{slug}.log",
            }
        )
        return f"Launched {worker['name']} ({role}) for '{objective}' (folder {slug}/)."

    return launch_worker


def _prefer_endfield_objective(role: str, objective: str) -> str:
    """If the model invents classic-AK wording (or a tiny stub), swap in the locked brief.

    Soft cases keep the model's text; ``GAME_TASK`` still injects lore bans either way.
    """
    low = objective.lower()
    smell = (
        "rhodes",
        "amiya",
        "exusiai",
        "silverash",
        "deployment point",
        " redeploy",
        "tower defense",
        "tower-defence",
        "oriopathy",
    )
    if any(s in low for s in smell) or len(objective.strip()) < 40:
        return lore.preferred_objective(role)
    return objective.strip()

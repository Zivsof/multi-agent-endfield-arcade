"""Worker manifest: who can build, which role, how to spawn them.

Used by:
  - Step 2 ``session.run_session`` → ``discover()`` to pick the team from ``--only`` / ``--skip``
  - Step 5 ``launch_worker`` → ``launch_argv()`` to build the subprocess command line

Each worker dict eventually gains ``slug`` (site folder name, usually same as ``key``).
Note: code for Pydantic lives under ``workers/pydantic_ai/`` but the site slug is
``pydantic`` (key), so the arcade URL is ``site/pydantic/game.html``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# Hard-coded team. ``key`` is what the orchestrator LLM passes to launch_worker.
# ``default_role`` locks curriculum slice (combat / operators / …) in lore.py.
WORKERS = [
    {
        "key": "strands",
        "name": "AWS Strands",
        "colour": "cyan",
        "file": "workers/strands/strands_worker.py",
        "runner": "python",
        "default_role": "combat",
    },
    {
        "key": "pydantic",
        "name": "Pydantic AI",
        "colour": "green",
        "file": "workers/pydantic_ai/pydantic_worker.py",
        "runner": "python",
        "default_role": "operators",
    },
    {
        "key": "maf",
        "name": "Microsoft Agent Framework",
        "colour": "magenta",
        "file": "workers/maf/maf_worker.py",
        "runner": "python",
        "default_role": "aic_factory",
    },
    {
        "key": "agno",
        "name": "Agno",
        "colour": "yellow",
        "file": "workers/agno/agno_worker.py",
        "runner": "python",
        "default_role": "exploration",
    },
    {
        "key": "mastra",
        "name": "Mastra",
        "colour": "blue",
        "file": "workers/mastra/worker.ts",
        "runner": "node",
        "default_role": "progression",
    },
]


def discover(skip: tuple[str, ...] = (), only: tuple[str, ...] = ()) -> list[dict]:
    """Return workers whose files exist, filtered by CLI flags.

    Rules:
      1. If ``only`` is non-empty, keep only those keys (``--skip`` is ignored).
      2. Else drop any key listed in ``skip``.
      3. Skip entries whose ``file`` is missing on disk.
      4. Attach ``slug`` (= ``key``) for the ``site/{slug}/`` output folder.
    """
    found = []
    for worker in WORKERS:
        key = worker["key"]
        if only and key not in only:
            continue
        if not only and key in skip:
            continue
        path = ROOT / worker["file"]
        if path.exists():
            found.append({**worker, "slug": key})
    return found


def launch_argv(worker: dict, task_id: int, board_path: Path) -> list[str]:
    """Build the argv list for ``subprocess.Popen`` (Step 5).

    Python workers: ``uv run path/to/worker.py <goal_id> <board_path>``
    Mastra: ``npx tsx path/to/worker.ts <goal_id> <board_path>``

    The child reads ``goal_id`` to claim the board row and ``board_path`` (or
    ``BOARD_PATH`` env) to open the same SQLite file as the orchestrator.
    """
    path = str((ROOT / worker["file"]).resolve())
    if worker["runner"] == "python":
        return [shutil.which("uv") or "uv", "run", path, str(task_id), str(board_path)]
    return [shutil.which("npx") or "npx", "tsx", path, str(task_id), str(board_path)]


def normalize_objective(objective: str) -> str:
    """Lowercase + collapse whitespace so duplicate curriculum topics compare equal."""
    return " ".join(objective.lower().split())

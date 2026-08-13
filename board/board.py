"""Shared SQLite todo board — coordination between orchestrator and workers.

Schema (table ``todos``):
  - A **goal** has ``parent_id IS NULL`` (e.g. the full GAME_TASK text from Step 5).
  - A **step** has ``parent_id = goal_id`` (planned by the worker in Step 6).
  - ``status``: pending → in_progress → done; ``result`` holds a short completion note.

``BOARD_PATH`` comes from the environment (set in ``main.py`` to ``site/board.sqlite``).
WAL mode lets the orchestrator and several worker processes share one file safely.

Orchestrator uses this module via ``from board import board as board_api``.
Each worker ships a near-identical copy under ``workers/*/board.py`` that reads the
same ``BOARD_PATH`` so they do not import across the project root.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from rich.console import Console

BOARD_PATH = Path(os.environ.get("BOARD_PATH", Path(__file__).resolve().parent.parent / "site" / "board.sqlite"))


def _connect(path: Path = BOARD_PATH) -> sqlite3.Connection:
    """Open SQLite with row dicts, WAL journal, and a busy timeout for concurrent writers."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def reset_board(path: Path = BOARD_PATH) -> None:
    """Drop and recreate ``todos`` — called at the start of each orchestrator ``run()``."""
    with _connect(path) as conn:
        conn.execute("DROP TABLE IF EXISTS todos")
        conn.execute(
            """CREATE TABLE todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER,
                task TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                result TEXT NOT NULL DEFAULT ''
            )"""
        )


def add_goal(task: str, path: Path = BOARD_PATH) -> int:
    """Insert a top-level goal (Step 5); return its integer id for the worker argv."""
    with _connect(path) as conn:
        cur = conn.execute("INSERT INTO todos (task) VALUES (?)", (task,))
        return cur.lastrowid


def add_step(goal_id: int, task: str, path: Path = BOARD_PATH) -> int:
    """Insert a child step under a goal (Step 6 ``plan_steps``)."""
    with _connect(path) as conn:
        cur = conn.execute(
            "INSERT INTO todos (parent_id, task) VALUES (?, ?)", (goal_id, task)
        )
        return cur.lastrowid


def list_todos(path: Path = BOARD_PATH) -> list[dict]:
    """Return every todo row (standalone demos / debugging). Prefer scoped list in arcade mode."""
    with _connect(path) as conn:
        rows = conn.execute(
            "SELECT id, parent_id, task, status, result FROM todos ORDER BY id"
        ).fetchall()
        return [dict(row) for row in rows]


def list_goal_and_steps(goal_id: int, path: Path = BOARD_PATH) -> list[dict]:
    """Scoped board view: one goal and only its steps (so parallel workers ignore siblings)."""
    with _connect(path) as conn:
        rows = conn.execute(
            """SELECT id, parent_id, task, status, result FROM todos
               WHERE id = ? OR parent_id = ? ORDER BY id""",
            (goal_id, goal_id),
        ).fetchall()
        return [dict(row) for row in rows]


def claim_todo(task_id: int, path: Path = BOARD_PATH) -> None:
    """Mark a todo ``in_progress`` (worker claims its goal at Step 6 start)."""
    with _connect(path) as conn:
        conn.execute("UPDATE todos SET status = 'in_progress' WHERE id = ?", (task_id,))


def complete_todo(task_id: int, result: str, path: Path = BOARD_PATH) -> None:
    """Mark a todo ``done`` and store a short result string."""
    with _connect(path) as conn:
        conn.execute(
            "UPDATE todos SET status = 'done', result = ? WHERE id = ?",
            (result, task_id),
        )


def show_board(path: Path = BOARD_PATH) -> None:
    """Pretty-print goals and steps to the terminal (Rich)."""
    todos = list_todos(path)
    lines = []
    for goal in [t for t in todos if t["parent_id"] is None]:
        lines.append(_format(goal, "Goal", ""))
        for step in [t for t in todos if t["parent_id"] == goal["id"]]:
            lines.append(_format(step, "Step", "  "))
    if lines:
        Console().print("\n".join(lines), soft_wrap=True)


def _format(todo: dict, kind: str, indent: str) -> str:
    """Rich markup for one board row (green strike = done, yellow = in progress)."""
    label = f"{indent}{kind} #{todo['id']}: {todo['task']}"
    if todo["status"] == "done":
        line = f"[green][strike]{label}[/strike][/green]"
        if todo["result"]:
            line += f"  [dim]{todo['result']}[/dim]"
        return line
    if todo["status"] == "in_progress":
        return f"[yellow]{label}[/yellow]"
    return label

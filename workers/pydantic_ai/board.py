"""SQLite todo board (worker-local copy; BOARD_PATH from env)."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from rich.console import Console

BOARD_PATH = Path(os.environ.get("BOARD_PATH", Path(__file__).resolve().parent / "board.sqlite"))


def _connect(path: Path = BOARD_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def reset_board(path: Path = BOARD_PATH) -> None:
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
    with _connect(path) as conn:
        cur = conn.execute("INSERT INTO todos (task) VALUES (?)", (task,))
        return cur.lastrowid


def add_step(goal_id: int, task: str, path: Path = BOARD_PATH) -> int:
    with _connect(path) as conn:
        cur = conn.execute(
            "INSERT INTO todos (parent_id, task) VALUES (?, ?)", (goal_id, task)
        )
        return cur.lastrowid


def list_todos(path: Path = BOARD_PATH) -> list[dict]:
    with _connect(path) as conn:
        rows = conn.execute(
            "SELECT id, parent_id, task, status, result FROM todos ORDER BY id"
        ).fetchall()
        return [dict(row) for row in rows]


def list_goal_and_steps(goal_id: int, path: Path = BOARD_PATH) -> list[dict]:
    with _connect(path) as conn:
        rows = conn.execute(
            """SELECT id, parent_id, task, status, result FROM todos
               WHERE id = ? OR parent_id = ? ORDER BY id""",
            (goal_id, goal_id),
        ).fetchall()
        return [dict(row) for row in rows]


def claim_todo(task_id: int, path: Path = BOARD_PATH) -> None:
    with _connect(path) as conn:
        conn.execute("UPDATE todos SET status = 'in_progress' WHERE id = ?", (task_id,))


def complete_todo(task_id: int, result: str, path: Path = BOARD_PATH) -> None:
    with _connect(path) as conn:
        conn.execute(
            "UPDATE todos SET status = 'done', result = ? WHERE id = ?",
            (result, task_id),
        )


def show_board(path: Path = BOARD_PATH) -> None:
    todos = list_todos(path)
    lines = []
    for goal in [t for t in todos if t["parent_id"] is None]:
        lines.append(_format(goal, "Goal", ""))
        for step in [t for t in todos if t["parent_id"] == goal["id"]]:
            lines.append(_format(step, "Step", "  "))
    if lines:
        Console().print("\n".join(lines), soft_wrap=True)


def _format(todo: dict, kind: str, indent: str) -> str:
    label = f"{indent}{kind} #{todo['id']}: {todo['task']}"
    if todo["status"] == "done":
        line = f"[green][strike]{label}[/strike][/green]"
        if todo["result"]:
            line += f"  [dim]{todo['result']}[/dim]"
        return line
    if todo["status"] == "in_progress":
        return f"[yellow]{label}[/yellow]"
    return label

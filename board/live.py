"""Live Rich view of the shared board while workers run (Step 7).

``wait_for_team`` calls ``render(team.registry)`` in a loop. Each call re-reads
``site/board.sqlite`` so you see goals/steps flip pending → in_progress → done as
inner workers (Step 6) update the board — without the orchestrator parsing logs.

``registry`` maps board goal_id → worker dict (name, colour, objective) so goals
show as ``AWS Strands: <objective>`` in the worker's catalog colour instead of the
raw GAME_TASK blob.
"""

from __future__ import annotations

from rich.console import Console, Group
from rich.text import Text

from board import board as board_api

# Shared console so orchestrator dim-italic text and the live board use one terminal.
console = Console()


def _line(todo: dict, colour: str, label: str, indent: str = "") -> Text:
    """One board row: strike+dim if done, bold if in_progress, plain otherwise."""
    text = Text(indent)
    if todo["status"] == "done":
        text.append(label, style=f"{colour} dim strike")
        if todo["result"]:
            text.append(f"   {todo['result']}", style="dim")
    elif todo["status"] == "in_progress":
        text.append(label, style=f"bold {colour}")
    else:
        text.append(label, style=colour)
    return text


def render(registry: dict[int, dict]) -> Group:
    """Build a Rich ``Group`` of goal + indented step lines (+ colour legend).

    Called repeatedly; always a fresh snapshot from SQLite (WAL-safe with workers).
    """
    todos = board_api.list_todos()
    # parent_id None → goals; parent_id = goal id → steps under that goal.
    children: dict[int | None, list[dict]] = {}
    for todo in todos:
        children.setdefault(todo["parent_id"], []).append(todo)

    lines: list[Text] = []
    for goal in children.get(None, []):
        worker = registry.get(goal["id"])
        colour = worker["colour"] if worker else "white"
        if worker:
            objective = worker.get("objective")
            label = f"{worker['name']}: {objective}" if objective else worker["name"]
        else:
            # Goal not in registry (unusual) — show a truncated raw task string.
            label = goal["task"][:48]
        lines.append(_line(goal, colour, label))
        for step in children.get(goal["id"], []):
            lines.append(_line(step, colour, step["task"], indent="    "))

    legend = Text("\n")
    seen = set()
    for worker in registry.values():
        if worker["name"] in seen:
            continue
        seen.add(worker["name"])
        legend.append(f"{worker['name']}  ", style=worker["colour"])
    lines.append(legend)
    return Group(*lines)

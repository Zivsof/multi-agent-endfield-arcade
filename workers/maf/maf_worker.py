"""MAF worker — Day-5 shared board mode (Endfield arcade)."""

from __future__ import annotations

import asyncio
import os
import sys
import warnings
from pathlib import Path

TASK_ID = int(sys.argv[1]) if len(sys.argv) > 2 else None
if TASK_ID is not None:
    os.environ.setdefault("BOARD_PATH", sys.argv[2])

warnings.filterwarnings("ignore", message=r".*experimental.*")

from dotenv import load_dotenv  # noqa: E402
from agent_framework import Agent, MCPStdioTool  # noqa: E402
from agent_framework.openai import OpenAIChatClient  # noqa: E402

import board  # noqa: E402

load_dotenv(override=True)

MODEL = os.environ.get("WORKER_MODEL", "gpt-5.4-mini")
WORKSPACE = Path(__file__).resolve().parent / "workspace"
GOAL = "Read notes.txt, translate its contents into natural Spanish, and write the Spanish to spanish.txt."
WORK_DIR = WORKSPACE if TASK_ID is None else Path(sys.argv[2]).resolve().parent

client = OpenAIChatClient(model=MODEL)

SCOPED = (
    "When working a claimed task id, call show_todos to see ONLY that goal and its steps "
    "— ignore other builders' work."
)


def show_todos() -> list[dict]:
    """List todos for your goal only (Day 5) or the whole board (standalone)."""
    if TASK_ID is not None:
        return board.list_goal_and_steps(TASK_ID)
    return board.list_todos()


def plan_steps(goal_id: int, steps: list[str]) -> dict:
    """Break a goal into ordered steps on the board."""
    return {"goal_id": goal_id, "step_ids": [board.add_step(goal_id, step) for step in steps]}


def complete_task(task_id: int, result: str) -> dict:
    """Mark a todo done and record a short result."""
    board.complete_todo(task_id, result)
    return {"task_id": task_id, "status": "done"}


INSTRUCTIONS = f"""
You are a careful worker with a shared todo board and a set of file tools.
{SCOPED}
Take the pending goal and see it through. Plan steps on the board, use file tools, mark done, close the goal.
"""


def seed() -> int:
    board.reset_board()
    WORKSPACE.mkdir(exist_ok=True)
    (WORKSPACE / "spanish.txt").unlink(missing_ok=True)
    goal_id = board.add_goal(GOAL)
    board.claim_todo(goal_id)
    return goal_id


async def main() -> None:
    if TASK_ID is None:
        goal_id = seed()
        print(f"Seeded goal {goal_id}: {GOAL}\n")
        message = "Please work the pending goal on the board."
    else:
        board.claim_todo(TASK_ID)
        message = (
            f"You have claimed task #{TASK_ID} on the shared board. Work only that task and its steps. "
            f"When the work is built and checked, mark task #{TASK_ID} itself done with complete_task, then stop."
        )

    filesystem = MCPStdioTool(
        name="filesystem",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", str(WORK_DIR)],
        cwd=str(WORK_DIR),
    )
    async with filesystem:
        worker = Agent(
            client=client,
            instructions=INSTRUCTIONS,
            tools=[show_todos, plan_steps, complete_task, filesystem],
        )
        await worker.run(message)

    if TASK_ID is None:
        print("\nBoard after the run:")
        board.show_board()


if __name__ == "__main__":
    asyncio.run(main())

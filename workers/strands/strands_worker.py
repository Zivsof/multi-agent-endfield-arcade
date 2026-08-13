"""Step 6 — AWS Strands inner worker (child process started by Step 5 ``launch_worker``).

This is a **different** agent stack from the orchestrator:
  - Outer loop: Google ADK + Gemini (``orchestrator/agent.py``)
  - Inner loop (this file): AWS Strands + OpenAI (``WORKER_MODEL``)

How it is started (argv from ``catalog.launch_argv``)::

    uv run strands_worker.py <goal_id> <board_path>

Then:
  1. Claim goal ``goal_id`` on the shared SQLite board (status → in_progress).
  2. Run a Strands ``Agent`` with board tools + MCP filesystem rooted at ``site/``.
  3. Agent reads the full ``GAME_TASK`` via ``show_todos``, plans steps, writes
     ``site/{slug}/game.html|css|js``, completes todos, then the process exits.

Standalone mode (no argv): seeds a tiny Spanish-translation demo under ``workspace/``.
Arcade mode always passes ``goal_id`` + ``board_path``.

Debug: ``site/logs/strands.log`` (tee'd by the parent ``launch()``).
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

# Arcade launch: argv[1]=goal id, argv[2]=path to site/board.sqlite.
TASK_ID = int(sys.argv[1]) if len(sys.argv) > 2 else None
if TASK_ID is not None:
    os.environ.setdefault("BOARD_PATH", sys.argv[2])

from dotenv import load_dotenv  # noqa: E402
from strands import Agent, tool  # noqa: E402
from strands.models.openai import OpenAIModel  # noqa: E402
from strands.tools.mcp import MCPClient  # noqa: E402
from mcp import stdio_client, StdioServerParameters  # noqa: E402

import board  # noqa: E402  # workers/strands/board.py — same schema as project board/

load_dotenv(override=True)

MODEL = os.environ.get("WORKER_MODEL", "gpt-5.4-mini")
WORKSPACE = Path(__file__).resolve().parent / "workspace"
GOAL = "Read notes.txt, translate its contents into natural Spanish, and write the Spanish to spanish.txt."
# Arcade: WORK_DIR = parent of board.sqlite = site/ (file tools may write strands/ there).
# Standalone: WORK_DIR = local workspace/ for the Spanish demo.
WORK_DIR = WORKSPACE if TASK_ID is None else Path(sys.argv[2]).resolve().parent

model = OpenAIModel(client_args={"api_key": os.environ["OPENAI_API_KEY"]}, model_id=MODEL)

SCOPED = """
When working a claimed task id, call show_todos to see ONLY that goal and its steps — ignore other builders' work.
"""


@tool
def show_todos() -> list[dict]:
    """List todos for your goal only (Day 5) or the whole board (standalone)."""
    if TASK_ID is not None:
        return board.list_goal_and_steps(TASK_ID)
    return board.list_todos()


@tool
def plan_steps(goal_id: int, steps: list[str]) -> dict:
    """Break a goal into ordered steps on the board."""
    return {"goal_id": goal_id, "step_ids": [board.add_step(goal_id, step) for step in steps]}


@tool
def complete_task(task_id: int, result: str) -> dict:
    """Mark a todo done and record a short result."""
    board.complete_todo(task_id, result)
    return {"task_id": task_id, "status": "done"}


INSTRUCTIONS = """
You are a careful worker with a shared todo board and a set of file tools.
""" + SCOPED + """
Take the pending goal and see it through. Begin by laying out a short plan: the handful of concrete steps the work itself breaks down into, added to the board under the goal. Then carry them out with your file tools, marking each step done as you finish it. Once the steps are all done, close the goal. Your files live in the single folder your tools are allowed to use.
"""

# MCP filesystem server: LLM gets read/write/list tools scoped to WORK_DIR only.
filesystem = MCPClient(
    lambda: stdio_client(
        StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", str(WORK_DIR)],
            cwd=str(WORK_DIR),
        ),
        errlog=subprocess.DEVNULL,
    ),
    startup_timeout=60,
)


def seed() -> int:
    """Standalone demo only: reset board, add Spanish-translation goal, claim it."""
    board.reset_board()
    WORKSPACE.mkdir(exist_ok=True)
    (WORKSPACE / "spanish.txt").unlink(missing_ok=True)
    goal_id = board.add_goal(GOAL)
    board.claim_todo(goal_id)
    return goal_id


async def main() -> None:
    """Claim work (or seed demo), run the Strands agent loop, exit when done."""
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

    worker = Agent(
        model=model,
        system_prompt=INSTRUCTIONS,
        tools=[show_todos, plan_steps, complete_task, filesystem],
    )
    # Agent loop: typically show_todos → plan_steps → write files → complete_task → stop.
    await worker.invoke_async(message)

    if TASK_ID is None:
        print("\nBoard after the run:")
        board.show_board()


if __name__ == "__main__":
    asyncio.run(main())

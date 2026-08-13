"""Step 9 — ADK tool ``relaunch_worker``: one repair attempt max per slug.

Agent view: after ``test_game`` returns broken/unknown, call::

    relaunch_worker(framework="strands", problem="<exact reason from test_game>")

Python view:
  1. Refuse a second fix if ``slug`` is already in ``team.fixed``.
  2. Mark ``repaired=True`` on the run entry (so the next ``test_game`` uses ``regate``).
  3. Add a new board goal with ``FIX_TASK`` (symptom = the problem string).
  4. ``launch`` another subprocess into ``team.pending`` (same worker, new goal_id).

Then the orchestrator should call ``wait_for_team`` again, then ``test_game`` again.
If the gate still fails after repair → ``repaired_but_gate_failed`` (no endless loop).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from board import board as board_api
from orchestrator.content import prompts
from orchestrator.tools.launch import launch

if TYPE_CHECKING:
    from orchestrator.agent import Team


def make_relaunch_worker(team: "Team"):
    """Return the ``relaunch_worker`` tool bound to this run's ``Team``."""

    def relaunch_worker(framework: str, problem: str) -> str:
        """Send a builder back once to fix its game. Echo the problem from test_game.

        Args:
            framework: framework key.
            problem: exact reason from test_game (gate or QA).
        """
        worker = team.by_key.get(framework)
        if worker is None:
            return f"No builder named '{framework}'."
        slug = worker["slug"]
        # Hard cap: each game gets at most one repair in a run.
        if slug in team.fixed:
            return f"{worker['name']} already had its one fix; leaving as is."
        team.fixed.add(slug)
        team.run_entries[slug]["repaired"] = True
        objective = team.objectives.get(slug, "")
        # FIX_TASK tells the worker *what broke* and what contracts to keep.
        text = prompts.FIX_TASK.format(
            slug=slug, objective=objective, symptom=problem, language=team.theme
        )
        goal_id = board_api.add_goal(text)
        team.registry[goal_id] = {**worker, "objective": objective}
        # Same launch helper as Step 5 — new process, log tee, pending entry.
        team.pending.append(launch(goal_id, worker, team.board_path, team.site_dir))
        return f"Sent {worker['name']} back to fix ({slug}/): {problem}"

    return relaunch_worker

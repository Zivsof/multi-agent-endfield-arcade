"""Orchestrator ADK tools package — factories assembled by ``make_tools``.

Why factories (``make_author_style(team)`` → inner ``author_style``)?
  Google ADK needs a **callable** with a docstring and typed args the LLM can fill.
  It does **not** require nested functions. We use factories so each tool's *public*
  signature stays small (what the agent decides) while paths / pending procs stay
  bound in Python (what the app already knows).

  Example: the agent sees ``author_style()`` with no args, not
  ``author_style(theme=…, site_dir=…)`` which it would invent badly.

See LEARNING.md Section 2 for the typical call order.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from orchestrator.tools.hub import make_author_style, make_build_hub
from orchestrator.tools.launch import launch, make_launch_worker, terminate
from orchestrator.tools.relaunch import make_relaunch_worker
from orchestrator.tools.test_game import make_test_game
from orchestrator.tools.wait import make_wait_for_team

if TYPE_CHECKING:
    from orchestrator.agent import Team

__all__ = ["launch", "terminate", "make_tools"]


def make_tools(team: "Team") -> list:
    """Build the six callables registered on the orchestrator ``LlmAgent``.

    Order here is documentation for humans; the LLM may call them in any order
    (the system prompt recommends style → launch all → wait → test → repair → hub).
    """
    return [
        make_author_style(team),  # Step 4 — site/common.css
        make_launch_worker(team),  # Step 5 — board goal + subprocess
        make_wait_for_team(team),  # Step 7 — block until workers exit
        make_test_game(team),  # Step 8 — gate then Playwright QA
        make_relaunch_worker(team),  # Step 9 — one repair max
        make_build_hub(team),  # Step 10 — site/index.html
    ]

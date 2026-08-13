"""ADK tools for shared house style (Step 4) and hub page (Step 10).

These wrappers are thin: ADK registers the inner functions; real work lives in
``orchestrator.site_build.art_director``. Factories bind ``team`` so the LLM never passes paths.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from orchestrator.site_build import art_director as site_style

if TYPE_CHECKING:
    from orchestrator.agent import Team


def make_author_style(team: "Team"):
    """Return the ``author_style`` tool for this run's ``Team``.

    Agent view: call ``author_style()`` with no arguments.
    Python view: write ``site/common.css`` using ``team.theme`` / ``team.site_dir``.
    """

    async def author_style() -> str:
        """Author the arcade's shared house style (common.css). Do this once, before the builders start."""
        # Docstring above is what Gemini reads as the tool description.
        await site_style.author_style(team.theme, team.site_dir)
        return "Authored common.css, the shared house style for the arcade."

    return author_style


def make_build_hub(team: "Team"):
    """Return the ``build_hub`` tool (Step 10 — after games exist).

    Agent view: ``build_hub()`` with no args.
    Python view: ``team.finished_games()`` (this run + disk siblings) → ``art_director.build_hub``.
    """

    async def build_hub() -> str:
        """Author index.html linking finished games (including disk-only siblings)."""
        games = team.finished_games()
        if not games:
            return "No finished games to link yet; build some first."
        await site_style.build_hub(team.theme, games, team.site_dir)
        return f"Authored index.html linking {len(games)} game(s): {', '.join(g['label'] for g in games)}."

    return build_hub

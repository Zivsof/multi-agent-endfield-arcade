"""Step 3 — outer Google ADK orchestrator: Team state + LLM run loop.

Called by ``session.run_session`` via ``run(theme, workers, site_dir, board_path)``.

Mental model:
  - The **LLM** (Gemini) is the project manager. It decides *when* to call tools.
  - **Python tools** (``orchestrator/tools/*``) do the real work: write CSS, spawn
    workers, wait, gate+QA, build hub.
  - ``Team`` is shared memory every tool reads/writes (objectives, pending procs,
    run-report entries). It is *not* an ADK concept — it is ours.

Flow inside ``run()``:
  1. Ensure ``site/`` and ``site/logs/`` exist.
  2. Reset the SQLite board (fresh goals for this run; disk games are kept).
  3. Build ``Team``, then ``asyncio.run(_run(team))`` — ADK agent event loop.
  4. ``_ensure_site`` safety net (CSS gate / hub template if the LLM bailed early).
  5. Write ``site/run_report.json``.

Tools the agent receives (typical order): author_style → launch_worker →
wait_for_team → test_game → relaunch_worker → build_hub.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path

from quiet import silence

silence()

from google.adk.agents import LlmAgent  # noqa: E402
from google.adk.agents.invocation_context import LlmCallsLimitExceededError  # noqa: E402
from google.adk.agents.run_config import RunConfig  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402

import config  # noqa: E402
from board import board as board_api  # noqa: E402
from board import live as live_board  # noqa: E402
from orchestrator import report  # noqa: E402
from orchestrator.content import lore, prompts  # noqa: E402
from orchestrator.gates import game_gate  # noqa: E402
from orchestrator.site_build import art_director as site_style  # noqa: E402
from orchestrator.tools import make_tools  # noqa: E402

_APP = "endfield_arcade"
# Hard cap on LLM round-trips so a confused orchestrator cannot burn unbounded tokens.
_MAX_TURNS = 80
GAME_FILES = game_gate.GAME_FILES
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def _read_title(game_html: Path) -> str:
    """Pull ``<title>…</title>`` from a game for hub card labels; empty if missing."""
    try:
        match = _TITLE_RE.search(game_html.read_text(encoding="utf-8"))
    except OSError:
        return ""
    return match.group(1).strip() if match else ""


def is_built(folder: Path) -> bool:
    """True when ``game.html``, ``game.css``, and ``game.js`` all exist and are non-empty."""
    return all((folder / f).exists() and (folder / f).stat().st_size for f in GAME_FILES)


class Team:
    """Shared run state for every orchestrator tool (clipboard, not an ADK type).

    Tools close over one ``Team`` instance when ``make_tools(team)`` builds them, so
    ``launch_worker`` can append to ``pending`` and ``wait_for_team`` can drain it
    without the LLM passing paths or process handles.
    """

    def __init__(self, theme: str, workers: list[dict], site_dir: Path, board_path: Path) -> None:
        self.theme = theme
        self.language = theme  # alias for course-shaped helpers that still say "language"
        self.workers = workers
        self.site_dir = site_dir
        self.board_path = board_path
        # Fast lookup: launch_worker("strands", …) → worker dict.
        self.by_key = {w["key"]: w for w in workers}
        self.by_slug = {w["slug"]: w for w in workers}
        # slug → curriculum objective assigned this run.
        self.objectives: dict[str, str] = {}
        # board goal_id → worker info (for the Rich live board while waiting).
        self.registry: dict[int, dict] = {}
        # Subprocesses started by launch_worker, consumed by wait_for_team.
        self.pending: list[dict] = []  # each: {slug, proc, log, started}
        # Slugs that already got one relaunch_worker repair (max one fix each).
        self.fixed: set[str] = set()
        self.started_at = datetime.now(timezone.utc)
        # Per-worker rows later written to site/run_report.json.
        self.run_entries: dict[str, dict] = {
            w["slug"]: report.empty_worker_entry(w["slug"], w.get("default_role", ""))
            for w in workers
        }
        # Normalized objective strings already handed out (block duplicates).
        self._seen_objectives: set[str] = set()

    def _built(self, slug: str) -> bool:
        """Whether ``site/{slug}/`` has a complete three-file game."""
        return is_built(self.site_dir / slug)

    def status(self) -> str:
        """Human-readable built / NOT built lines returned by ``wait_for_team``."""
        lines = []
        for w in self.workers:
            slug = w["slug"]
            objective = self.objectives.get(slug)
            who = f"{w['name']} ({objective})" if objective else w["name"]
            lines.append(f"  {who} [{slug}/]: {'built' if self._built(slug) else 'NOT built'}")
        return "Team status:\n" + "\n".join(lines)

    def finished_games(self) -> list[dict]:
        """Games to link on the hub: this run's workers plus any other built folders on disk.

        ``--only strands`` does not delete sibling folders from earlier runs. Those
        appear here as ``disk_only`` report entries so the hub can still link them.
        """
        games = []
        seen = set()
        for worker in self.workers:
            slug = worker["slug"]
            if not self._built(slug):
                continue
            seen.add(slug)
            label = _read_title(self.site_dir / slug / "game.html") or self.objectives.get(slug) or worker["name"]
            games.append({"label": label, "slug": slug})
        for child in sorted(self.site_dir.iterdir()):
            if not child.is_dir() or child.name in ("logs",) or child.name in seen:
                continue
            if is_built(child):
                label = _read_title(child / "game.html") or child.name
                games.append({"label": label, "slug": child.name})
                if child.name not in self.run_entries:
                    self.run_entries[child.name] = report.empty_worker_entry(
                        child.name, disk_only=True, built=True, launched=False
                    )
                else:
                    self.run_entries[child.name]["disk_only"] = True
                    self.run_entries[child.name]["built"] = True
        return games


def _build_agent(team: Team) -> LlmAgent:
    """Assemble the Google ADK ``LlmAgent``: system prompt + six tools bound to ``team``."""
    team_lines = lore.curriculum_lines_for_team(team.workers)
    instruction = prompts.ORCHESTRATOR_PROMPT.format(
        team=team_lines,
        lore_block=prompts.LORE_BLOCK,
    )
    return LlmAgent(
        name="orchestrator",
        model=config.ORCHESTRATOR_MODEL,
        instruction=instruction,
        tools=make_tools(team),
    )


async def _run(team: Team) -> None:
    """Drive the ADK agent until it stops, hits the turn budget, or errors.

    ``InMemoryRunner`` runs the agent in-process (no separate server). The opening
    ``UserContent`` is the kickoff message; the system prompt already lists the
    step recipe (style → launch → wait → test → repair → hub).
    """
    runner = InMemoryRunner(agent=_build_agent(team), app_name=_APP)
    try:
        session = await runner.session_service.create_session(app_name=_APP, user_id="orchestrator")
        async for event in runner.run_async(
            user_id="orchestrator",
            session_id=session.id,
            new_message=types.UserContent(
                "Build the Endfield (Talos-II) arcade using each builder's preferred curriculum "
                "objective. Author black/yellow/white style first, launch all builders, gate+QA, "
                "one repair max, then a designed hub with difficulty deep-links."
            ),
            run_config=RunConfig(max_llm_calls=_MAX_TURNS),
        ):
            # Stream any free-text the model emits (tool calls show up elsewhere).
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text and part.text.strip():
                        live_board.console.print(part.text.strip(), style="dim italic")
    except LlmCallsLimitExceededError:
        print(f"\n  NOTE: orchestrator reached its {_MAX_TURNS}-step budget; wrapping up.")
    except Exception as exc:
        # e.g. Gemini 429 — still run _ensure_site + report so partial work is usable.
        print(f"\n  NOTE: orchestrator stopped early ({type(exc).__name__}: {exc}); wrapping up.")
    finally:
        try:
            await runner.close()
        except Exception:
            pass


def _ensure_site(team: Team) -> None:
    """Safety net after the LLM loop: guarantee usable CSS + hub when games exist.

    If the orchestrator never called ``author_style`` / ``build_hub``, or wrote CSS
    that fails the design gate, write known-good templates so ``file://`` still works.
    """
    games = team.finished_games()
    css_path = team.site_dir / "common.css"
    if not css_path.exists() or not site_style.css_passes(css_path.read_text(encoding="utf-8")):
        site_style.write_template_style(team.site_dir)
        print("  NOTE: wrote/refreshed common.css (CSS gate / template).")
    hub = team.site_dir / "index.html"
    needs_hub = not hub.exists()
    if hub.exists() and games:
        text = hub.read_text(encoding="utf-8")
        if not any(f'{g["slug"]}/game.html' in text for g in games):
            needs_hub = True
        elif "nav-grid" not in text and "hero" not in text:
            needs_hub = True
    if needs_hub:
        site_style.write_template_hub(team.theme, games, team.site_dir)
        print("  NOTE: wrote/refreshed designed template index.html with finished games.")


def run(theme: str, workers: list[dict], site_dir: Path, board_path: Path) -> Team:
    """Public entry from the CLI (Step 2 → Step 3). Returns the filled ``Team``."""
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "logs").mkdir(parents=True, exist_ok=True)
    # Fresh todos for this run. Does not delete existing site/{slug}/ game folders.
    board_api.reset_board()
    team = Team(theme, workers, site_dir, board_path)
    asyncio.run(_run(team))
    _ensure_site(team)
    report.write_report(site_dir, team.started_at, list(team.run_entries.values()))
    return team

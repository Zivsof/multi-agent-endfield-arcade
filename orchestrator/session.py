"""Step 2 — arcade session: parse flags, pick workers, start or dry-run the orchestrator.

``main.py`` calls ``run_session()``. This module:
  - reads ``--only`` / ``--skip`` / ``--dry-run`` / ``--no-open`` via argparse
  - asks ``catalog.discover`` which builders exist after filtering
  - prints the planned team (role + preferred Endfield objective)
  - either stops (``--dry-run``) or calls ``agent.run`` (Step 3)
  - after the run, prints built/not-built and optionally opens the hub

Does not talk to the LLM itself — that starts inside ``orchestrator.agent.run``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import config
from orchestrator import catalog
from orchestrator import agent as orch
from orchestrator.content import lore
from qa import agent as qa_agent

# session.py lives in orchestrator/; parent.parent is the project root (same as main.py's ROOT).
ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
BOARD_PATH = SITE / "board.sqlite"


def parse_args() -> argparse.Namespace:
    """Turn command-line tokens into attributes (``args.only``, ``args.dry_run``, …).

    ``argparse`` is the stdlib CLI parser. Hyphen flags become snake_case attributes
    (``--dry-run`` → ``args.dry_run``). ``nargs="*"`` means zero or more values after
    the flag; ``action="store_true"`` means a boolean switch with no value.
    """
    parser = argparse.ArgumentParser(
        description="Build an Endfield learning arcade with the Week 5 team."
    )
    parser.add_argument(
        "--skip",
        nargs="*",
        default=[],
        help="worker keys to leave out (ignored if --only is set)",
    )
    parser.add_argument(
        "--only",
        nargs="*",
        default=[],
        help="if set, only these keys (wins over --skip); e.g. --only strands",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the team plan and exit — no LLM, no workers",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="do not open site/index.html in the browser when done",
    )
    return parser.parse_args()


def run_session() -> None:
    """Entry after bootstrap: filter catalog → print plan → run agent or dry-run."""
    args = parse_args()
    # Tuples: immutable snapshots of the flag lists for discover().
    only = tuple(args.only)
    skip = tuple(args.skip)
    workers = catalog.discover(skip=skip, only=only)
    if not workers:
        raise SystemExit("No worker files found. Vendor workers under workers/ first.")

    print(f"Assembling an {config.THEME} arcade with {len(workers)} builders:")
    for worker in workers:
        role = worker.get("default_role", "")
        # Preview of the locked curriculum brief (lore.py) for this role.
        preferred = lore.preferred_objective(role)[:72]
        # :<28 / :<14 = left-align into fixed column widths for readable output.
        print(f"  {worker['name']:<28} role={role:<14} -> folder {worker['slug']}/")
        print(f"    preferred: {preferred}…")

    if args.dry_run:
        print("\nDry run: stopping before the agent runs.")
        return

    # Step 3 starts here: Google ADK orchestrator + tools.
    print(f"\n{config.ORCHESTRATOR_MODEL} is leading the team. Watch the board fill in:\n")
    orch.run(config.THEME, workers, SITE, BOARD_PATH)

    print("\nFinal check:")
    for worker in workers:
        slug = worker["slug"]
        built = orch.is_built(SITE / slug)
        print(f"  {slug}: {'built' if built else 'NOT built'}")

    index = SITE / "index.html"
    if index.exists() and not args.no_open:
        qa_agent.open_site(index)
        print(f"\nOpen {index}")
    elif index.exists():
        print(f"\nHub ready at {index} (not opened)")

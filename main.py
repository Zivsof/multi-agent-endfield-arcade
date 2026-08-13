#!/usr/bin/env python3
"""Step 1 — process entry for the Endfield multi-agent arcade.

Run with::

    uv run python main.py --only strands --no-open

What this file does (before any agent runs):
  1. Puts the project root on ``sys.path`` so ``import orchestrator`` / ``import board`` work.
  2. Loads ``.env`` (API keys, optional model overrides).
  3. Pins ``BOARD_PATH`` to ``site/board.sqlite`` so the orchestrator and every worker
     subprocess share one SQLite todo board.
  4. Hands off to ``orchestrator.session.run_session`` (Step 2).

This file does **not** build games or call the LLM. It only bootstraps the environment.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Project root = directory that contains main.py, site/, workers/, orchestrator/.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Avoid mojibake when Rich / agents print Unicode on some terminals.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# override=True: values in .env win over empty shell exports of the same key.
load_dotenv(override=True)
# ADK/Gemini: use the consumer API key path, not Vertex AI, unless the user opts in.
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")

# Shared deliverable root + coordination DB. Workers inherit BOARD_PATH via env.
SITE = ROOT / "site"
BOARD_PATH = SITE / "board.sqlite"
os.environ["BOARD_PATH"] = str(BOARD_PATH)

import config  # noqa: E402  # after dotenv so env overrides apply

# Propagate the resolved worker model into child processes started later by launch_worker.
os.environ["WORKER_MODEL"] = config.WORKER_MODEL

from orchestrator.session import run_session  # noqa: E402

if __name__ == "__main__":
    run_session()

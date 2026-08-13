"""Env-overridable knobs for models, timeouts, and theme.

Read once at import time. Override without editing code, e.g.::

    ORCHESTRATOR_MODEL=gemini-3.1-flash-lite WORKER_MODEL=gpt-5.4-mini \\
      uv run python main.py --only strands
"""

import os

# Outer Google ADK orchestrator (Gemini). Cheaper default alternative: gemini-3.1-flash-lite.
ORCHESTRATOR_MODEL = os.environ.get("ORCHESTRATOR_MODEL", "gemini-3.5-flash")

# Inner framework workers (OpenAI for most Python workers). Cheaper: gpt-5.4-mini.
WORKER_MODEL = os.environ.get("WORKER_MODEL", "gpt-5.5")

# How long wait_for_team may wait before killing hung worker subprocesses.
WORKER_TIMEOUT_S = int(os.environ.get("WORKER_TIMEOUT_S", "300"))

# How long Playwright QA may spend judging one game.
QA_TIMEOUT_S = int(os.environ.get("QA_TIMEOUT_S", "150"))

# Arcade theme label (hub titles, prompts). Not a programming language.
THEME = "Endfield"

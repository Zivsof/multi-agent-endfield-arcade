# Architecture — nested multi-agent loops

```text
ADK orchestrator (decide → launch → wait → gate → QA → repair → hub)
        │
        ├── launch workers in parallel (subprocess + log tee)
        │         │
        │         ▼
        │   site/board.sqlite  ←── shared coordination
        │         │
        │         ▼
        │   site/{slug}/game.html|css|js
        │
        └── game_gate → Playwright QA → optional one relaunch → re-gate
```

**Entry:** `main.py` bootstraps env → `orchestrator.session.run_session` picks workers → `agent.run` (ADK loop).

**Outer loop:** Google ADK agent with tools `author_style`, `launch_worker`, `wait_for_team`, `test_game`, `relaunch_worker`, `build_hub`.

**Inner loop:** each framework worker plans steps on the board, uses filesystem MCP, completes its goal.

**Orchestrator package layout:**

```text
orchestrator/
  session.py, catalog.py, agent.py, report.py
  content/       # lore, prompts, disclaimer
  gates/         # game_gate, css_gate (deterministic)
  site_build/    # art_director (writes common.css + index.html)
  tools/         # ADK tool factories
```

**Contracts beyond a bare multi-agent demo:** deterministic game/CSS gates, structured QA verdict, no false WORKS on QA budget exhaust, per-slug logs, scoped board tools, catalog roles + unique objectives, disclaimer constant, `?difficulty=`, `--only`, hung-slug wait, `run_report.json`, re-gate after repair.

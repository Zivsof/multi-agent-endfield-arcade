# Dependencies

## This repo

Standalone `pyproject.toml` + `uv.lock` (created by `uv sync`).

```bash
uv sync
uv run python main.py --dry-run
uv run pytest
```

Keys: `GOOGLE_API_KEY` (ADK orchestrator / QA / style), `OPENAI_API_KEY` (most workers).

| Package | Used for |
|---------|----------|
| `google-adk[mcp]` | Outer orchestrator, art director, Playwright QA |
| `strands-agents[openai]` | Strands worker |
| `pydantic-ai-slim[mcp,openai]` | Pydantic AI worker |
| `agent-framework-*` | Microsoft Agent Framework (MAF) worker |
| `agno[mcp]` | Agno worker |
| `python-dotenv`, `rich` | Env + live board |
| `openai` | Shared OpenAI client for workers |

Mastra: Node 18+ and `npm install` inside `workers/mastra/` (separate from the Python env).

Dev: `pytest` via `uv sync --group dev` (or `uv sync` if you include the group).

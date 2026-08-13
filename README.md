# Multi-Agent Endfield Arcade

Unofficial fan learning arcade: five agent frameworks each build a browser mini-game that teaches a slice of *Arknights: Endfield*. A Google ADK orchestrator launches them in parallel over a shared SQLite board, gates + QA-checks each game, allows one repair, and assembles the hub.

**Pipeline:** author shared CSS → launch workers → wait on the board → acceptance gate → Playwright QA → optional one relaunch → build hub.

**Not affiliated** with Hypergryph / GRYPHLINE. Content is AI-generated — take with a grain of salt and verify via official or community sources outside this site.

## Architecture

See [docs/architecture.md](docs/architecture.md). Nested loops: ADK outer orchestrator · five inner workers · shared `site/board.sqlite` · static `site/` games.

| Framework key | Role |
|---------------|------|
| `strands` | Combat basics |
| `pydantic` | Operators & roles |
| `maf` | AIC / factory |
| `agno` | Exploration |
| `mastra` | Progression / gear |

## Requirements

- Python **≥ 3.12** and [uv](https://docs.astral.sh/uv/)
- Node **18+** (Mastra worker only)
- API keys: `GOOGLE_API_KEY` (orchestrator / style / QA), `OPENAI_API_KEY` (Python workers). OpenAI usage needs billing credits.

## Setup

```bash
cp .env.example .env   # add GOOGLE_API_KEY and OPENAI_API_KEY (.env is gitignored)
uv sync                # install Python deps from pyproject.toml
# Mastra worker (once):
cd workers/mastra && npm install && cd ../..
```

Env knobs: `ORCHESTRATOR_MODEL`, `WORKER_MODEL`, `WORKER_TIMEOUT_S`, `QA_TIMEOUT_S`, `QA_HEADLESS=1`. See [docs/deps.md](docs/deps.md).

## Run

```bash
uv run python main.py --dry-run
uv run python main.py --only strands --no-open
uv run python main.py --skip mastra
uv run python main.py                    # full team; opens hub unless --no-open
```

If both `--skip` and `--only` are set, **`--only` wins**. Partial reruns do **not** delete sibling `site/{slug}/` folders; the hub still links disk-finished games. Board SQLite may reset while old game files remain — see `site/run_report.json`.

## Outputs

After a successful run, open `site/index.html` via `file://`.

| Path | What it is |
|------|------------|
| `site/index.html` | Hub with Beginner / Veteran deep-links |
| `site/common.css` | Shared black / yellow / white house style |
| `site/{slug}/game.html\|css\|js` | One mini-game per framework |
| `site/logs/{slug}.log` | Worker subprocess log |
| `site/run_report.json` | Machine-readable run summary |

Games honor `?difficulty=beginner|veteran` and should include an in-game Beginner/Veteran control when possible.

## Design + lore

- House palette: **black / yellow / white** (`orchestrator/content/lore.py` design tokens + `common.css`).
- Curriculum locks Endfield / Talos-II topics and bans classic Arknights TD / Rhodes Island roster quizzes.
- Preferred objectives per role show on `--dry-run`.

## Tests

Contract tests only (no live agents / no API calls):

```bash
uv run pytest
```

## License

MIT — see [LICENSE](LICENSE).

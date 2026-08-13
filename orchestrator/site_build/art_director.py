"""Step 4 (and Step 10) — art director: LLM writes CSS/HTML with deterministic fallbacks.

``author_style`` (Step 4):
  1. Ask a small ADK ``LlmAgent`` (no tools) to write ``common.css`` from ``CSS_PROMPT``.
  2. Run ``gates.css_gate.check_common_css`` (Python rules, not another LLM).
  3. If fail → one ``CSS_REPAIR_PROMPT`` attempt → check again.
  4. If still fail → write ``_template_css()`` (known-good black/yellow/white).

``build_hub`` (Step 10) uses the same mini-agent pattern for ``index.html``, with
``_hub_ok`` / ``_template_hub`` as the HTML safety net.

Why a separate mini-agent? The orchestrator manages the whole run; CSS/HTML authoring
is a focused "return only file contents" job with a strict palette.
"""

from __future__ import annotations

from quiet import silence

silence()

from google.adk.agents import LlmAgent  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402

import config  # noqa: E402
from orchestrator.content import prompts  # noqa: E402
from orchestrator.content.disclaimer import DISCLAIMER  # noqa: E402
from orchestrator.content.lore import DESIGN_TOKENS  # noqa: E402
from orchestrator.gates import css_gate  # noqa: E402

_APP = "endfield_arcade"


async def author_style(theme: str, site_dir) -> None:
    """Generate → gate → one repair → template fallback; always leaves ``site/common.css``."""
    site_dir.mkdir(parents=True, exist_ok=True)
    css = await _safe(prompts.CSS_PROMPT)
    gate = css_gate.check_common_css(css)
    if not gate["ok"]:
        # Tell the model exactly which contract checks failed + a snippet of bad CSS.
        repair = prompts.CSS_REPAIR_PROMPT.format(
            failures=", ".join(gate["failures"]),
            snippet=css[:1200] if css else "(empty)",
        )
        css = await _safe(repair)
        gate = css_gate.check_common_css(css)
    if gate["ok"]:
        (site_dir / "common.css").write_text(css, encoding="utf-8")
    else:
        (site_dir / "common.css").write_text(_template_css(), encoding="utf-8")
        print(
            f"  NOTE: CSS gate failed ({', '.join(gate['failures'])}); used template."
        )


async def build_hub(theme: str, games: list[dict], site_dir) -> None:
    """Ask the art-director LLM for ``index.html``; fall back to designed template if plain."""
    site_dir.mkdir(parents=True, exist_ok=True)
    links = "; ".join(
        f'"{g["label"]}" at {g["slug"]}/game.html?difficulty=beginner'
        f' and veteran at {g["slug"]}/game.html?difficulty=veteran'
        for g in games
    )
    hub = await _safe(prompts.HUB_PROMPT.format(disclaimer=DISCLAIMER, links=links))
    hub_ok = _hub_ok(hub, games)
    (site_dir / "index.html").write_text(
        hub if hub_ok else _template_hub(theme, games), encoding="utf-8"
    )
    if not hub_ok:
        print(
            f"  NOTE: {config.ORCHESTRATOR_MODEL} hub too plain or incomplete; used designed template."
        )


async def _safe(prompt: str) -> str:
    """Call the art-director LLM; return empty string on any API/runtime failure."""
    try:
        return await _ask(prompt)
    except Exception:
        return ""


async def _ask(prompt: str) -> str:
    """One-shot ADK agent with no tools: user message = prompt, collect text parts."""
    agent = LlmAgent(
        name="art_director",
        model=config.ORCHESTRATOR_MODEL,
        instruction=(
            "You are a precise art director for an Endfield fan arcade. "
            "Return only the file contents asked for. Honor black/yellow/white. "
            "Never output cyan or purple accents."
        ),
    )
    runner = InMemoryRunner(agent=agent, app_name=_APP)
    try:
        session = await runner.session_service.create_session(app_name=_APP, user_id="orchestrator")
        parts: list[str] = []
        async for event in runner.run_async(
            user_id="orchestrator", session_id=session.id, new_message=types.UserContent(prompt)
        ):
            if event.content and event.content.parts:
                parts.extend(p.text for p in event.content.parts if p.text)
        # Models often wrap CSS/HTML in ``` fences despite instructions — strip them.
        return _strip_fences("".join(parts))
    finally:
        try:
            await runner.close()
        except Exception:
            pass


def write_template_style(site_dir) -> None:
    """Write known-good ``common.css`` (used by gate failure and ``_ensure_site``)."""
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "common.css").write_text(_template_css(), encoding="utf-8")


def css_passes(css: str) -> bool:
    """True if ``common.css`` meets the design contract in ``gates.css_gate``."""
    return css_gate.check_common_css(css)["ok"]


def write_template_hub(theme: str, games: list[dict], site_dir) -> None:
    """Write known-good ``index.html`` with hero + card grid + difficulty links."""
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "index.html").write_text(_template_hub(theme, games), encoding="utf-8")


def _hub_ok(html: str, games: list[dict]) -> bool:
    """Reject empty/plain hubs missing game links or layout hooks (nav-grid / hero / card)."""
    if "<" not in html or len(html) < 200:
        return False
    if not games:
        return True
    if not all(f'{g["slug"]}/game.html' in html for g in games):
        return False
    designed = any(token in html for token in ("nav-grid", 'class="card"', "class='card'", "hero"))
    return designed


def _strip_fences(text: str) -> str:
    """Remove a leading/trailing markdown code fence if the model wrapped the file."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _template_css() -> str:
    """Hand-written CSS that always passes ``check_common_css`` (includes ``a.btn`` reset)."""
    t = DESIGN_TOKENS
    return f"""\
:root {{
  --bg: {t['bg']};
  --panel: {t['panel']};
  --fg: {t['fg']};
  --muted: {t['muted']};
  --accent: {t['accent']};
  --accent-dim: {t['accent_dim']};
  --good: {t['good']};
  --bad: {t['bad']};
  --font: {t['font']};
  --radius: 4px;
  --gap: 1.25rem;
}}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; min-height: 100%; }}
body {{
  font-family: var(--font);
  background: var(--bg);
  color: var(--fg);
  line-height: 1.55;
}}
a {{ color: var(--accent); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
a.btn, a.btn:hover {{ border-bottom: none; text-decoration: none; }}
h1, h2, h3 {{ letter-spacing: 0.04em; margin: 0 0 0.6rem; font-weight: 700; }}
.hero {{
  padding: 3.5rem 1.5rem 2rem;
  border-bottom: 1px solid #222;
  background:
    linear-gradient(180deg, #121212 0%, var(--bg) 100%);
}}
.hero-brand {{
  font-size: clamp(2.4rem, 6vw, 4rem);
  color: var(--fg);
  text-transform: uppercase;
  letter-spacing: 0.12em;
}}
.hero-brand span {{ color: var(--accent); }}
.hero-lede {{ max-width: 36rem; color: var(--muted); margin: 0.75rem 0 0; }}
.wrap {{ max-width: 960px; margin: 0 auto; padding: 1.5rem; }}
.nav-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: var(--gap);
  list-style: none;
  margin: 1.5rem 0 0;
  padding: 0;
}}
.card {{
  background: var(--panel);
  border: 1px solid #2a2a2a;
  border-top: 3px solid var(--accent);
  border-radius: var(--radius);
  padding: 1.1rem 1.2rem;
}}
.card h2 {{ font-size: 1.05rem; }}
.card .meta {{ color: var(--muted); font-size: 0.9rem; margin: 0.4rem 0 0.9rem; }}
.card .links {{ display: flex; gap: 0.75rem; flex-wrap: wrap; align-items: center; }}
.btn, button {{
  font: inherit;
  border: 1px solid var(--accent);
  background: var(--accent);
  color: #111;
  padding: 0.55rem 1rem;
  border-radius: var(--radius);
  cursor: pointer;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}}
button.ghost, .btn.ghost {{
  background: transparent;
  color: var(--accent);
}}
.correct {{ color: var(--good); border-left: 3px solid var(--accent); padding-left: 0.6rem; }}
.wrong {{ color: var(--bad); border-left: 3px solid var(--bad); padding-left: 0.6rem; }}
.disclaimer {{
  font-size: 0.85rem;
  color: var(--muted);
  margin-top: 2.5rem;
  padding-top: 1rem;
  border-top: 1px solid #222;
}}
"""


def _template_hub(theme: str, games: list[dict]) -> str:
    """Minimal designed hub: ENDFIELD hero, card grid, beginner/veteran deep-links."""
    cards = []
    for g in games:
        slug = g["slug"]
        label = g["label"]
        cards.append(
            f'      <li class="card">\n'
            f"        <h2>{label}</h2>\n"
            f'        <p class="meta">Talos-II training module · {slug}</p>\n'
            f'        <div class="links">\n'
            f'          <a class="btn" href="{slug}/game.html?difficulty=beginner">Beginner</a>\n'
            f'          <a class="btn ghost" href="{slug}/game.html?difficulty=veteran">Veteran</a>\n'
            f"        </div>\n"
            f"      </li>"
        )
    grid = "\n".join(cards) if cards else "      <!-- no games yet -->"
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{theme} Learning Arcade</title>
  <link rel="stylesheet" href="common.css" />
</head>
<body>
  <header class="hero">
    <div class="wrap">
      <p class="hero-brand">END<span>FIELD</span></p>
      <p class="hero-lede">Unofficial Talos-II training sims — five agent frameworks, one arcade. Pick a module.</p>
    </div>
  </header>
  <main class="wrap">
    <h1>{theme} Learning Arcade</h1>
    <ul class="nav-grid">
{grid}
    </ul>
    <p class="disclaimer">{DISCLAIMER}</p>
  </main>
</body>
</html>
"""

"""Step 8 (browser half) — QA tester via Playwright MCP.

Used only after ``game_gate.check_game`` passes. Spins up an ADK agent with
Playwright MCP tools + a ``report_game`` callback. Opens the ``file://`` game URI,
clicks around, then must call ``report_game``.

Important: LLM call-budget exhaustion sets status ``unknown``, **not** ``works``.
``QA_HEADLESS=1`` adds ``--headless`` to the Playwright MCP args.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import webbrowser
from pathlib import Path

from quiet import silence

silence()

from google.adk.agents import LlmAgent  # noqa: E402
from google.adk.agents.invocation_context import LlmCallsLimitExceededError  # noqa: E402
from google.adk.agents.run_config import RunConfig  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams  # noqa: E402
from google.genai import types  # noqa: E402
from mcp import StdioServerParameters  # noqa: E402

import config  # noqa: E402
from orchestrator.content import prompts  # noqa: E402

_APP = "endfield_arcade"
_MAX_CALLS = 25
_CLOSE_TIMEOUT = 10


async def judge_game(theme: str, objective: str, uri: str) -> dict | None:
    """Return {works, reason, checks, status} or None if browser unavailable.

    status is works|broken|unknown. Budget exhaustion → unknown (not works).
    """
    verdict: dict = {}

    def report_game(works: bool, reason: str, checks: list[str] | None = None) -> dict:
        """Report whether the game works after playing it.

        Args:
            works: true if the game loads and plays correctly.
            reason: one short sentence on what you saw or what is broken.
            checks: short list of things you verified.
        """
        verdict["works"] = works
        verdict["reason"] = reason
        verdict["checks"] = checks or []
        verdict["status"] = "works" if works else "broken"
        # back-compat for course-style note field
        verdict["note"] = reason
        return {"recorded": True}

    args = ["-y", "@playwright/mcp@latest", "--browser", "chrome", "--isolated"]
    if os.environ.get("QA_HEADLESS") == "1":
        args.append("--headless")
    browser = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(command="npx", args=args),
            timeout=30.0,
        ),
        errlog=subprocess.DEVNULL,
    )

    agent = LlmAgent(
        name="qa_tester",
        model=config.ORCHESTRATOR_MODEL,
        instruction="You are a meticulous QA tester. Use the browser, then report_game.",
        tools=[browser, report_game],
    )
    runner = InMemoryRunner(agent=agent, app_name=_APP)
    try:
        session = await runner.session_service.create_session(app_name=_APP, user_id="qa")
        prompt = prompts.QA_PROMPT.format(objective=objective, uri=uri)
        try:
            async for _ in runner.run_async(
                user_id="qa",
                session_id=session.id,
                new_message=types.UserContent(prompt),
                run_config=RunConfig(max_llm_calls=_MAX_CALLS),
            ):
                pass
        except LlmCallsLimitExceededError:
            verdict.setdefault("works", False)
            verdict.setdefault("reason", "QA call budget exhausted without report_game; treating as unknown.")
            verdict.setdefault("checks", [])
            verdict["status"] = "unknown"
        return verdict or None
    finally:
        for close in (browser.close, runner.close):
            try:
                await asyncio.wait_for(close(), timeout=_CLOSE_TIMEOUT)
            except Exception:
                pass
        await asyncio.sleep(0.1)


def open_site(index_path: Path) -> None:
    webbrowser.open(index_path.resolve().as_uri())

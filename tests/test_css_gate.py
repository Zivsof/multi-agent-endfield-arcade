"""CSS gate tests for common.css."""

from __future__ import annotations

from pathlib import Path

from orchestrator.gates import css_gate
from orchestrator.site_build import art_director


def test_template_css_passes_gate():
    css = art_director._template_css()
    result = css_gate.check_common_css(css)
    assert result["ok"], result["failures"]


def test_broken_hub_css_fails_gate():
    """Regression: LLM CSS with underlined global links but no a.btn reset."""
    bad = """
    :root { --bg: #0a0a0a; --accent: #f5c518; }
    a { border-bottom: 1px solid var(--accent); }
    .btn { background: var(--accent); }
    .ghost { color: var(--accent); }
    .nav-grid {} .card {} .hero {} .disclaimer {} .correct {} .wrong {}
    """
    result = css_gate.check_common_css(bad)
    assert not result["ok"]
    assert "btn_link_underline_conflict" in result["failures"]


def test_css_passes_helper():
    assert art_director.css_passes(art_director._template_css())


def test_live_site_css_if_present():
    css_path = Path("site/common.css")
    if not css_path.exists():
        return
    result = css_gate.check_common_css(css_path.read_text(encoding="utf-8"))
    if not result["ok"]:
        fixed = art_director._template_css()
        assert css_gate.check_common_css(fixed)["ok"]

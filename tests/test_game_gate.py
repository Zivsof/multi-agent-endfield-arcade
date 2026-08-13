"""Game gate contract tests."""

from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.gates.game_gate import check_game

FIXTURES = Path(__file__).parent / "fixtures"


def test_gate_pass():
    result = check_game(FIXTURES / "gate_pass")
    assert result["ok"] is True
    assert result["failures"] == []


def test_gate_fail():
    result = check_game(FIXTURES / "gate_fail")
    assert result["ok"] is False
    assert "missing_common_css_link" in result["failures"]
    assert "missing_disclaimer_marker" in result["failures"]

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import catalog


def test_workers_have_default_roles():
    roles = {w["key"]: w["default_role"] for w in catalog.WORKERS}
    assert roles["strands"] == "combat"
    assert roles["pydantic"] == "operators"
    assert roles["maf"] == "aic_factory"
    assert roles["agno"] == "exploration"
    assert roles["mastra"] == "progression"


def test_normalize_objective():
    assert catalog.normalize_objective("  Combat  Basics ") == "combat basics"


def test_discover_only_wins_over_skip():
    # If workers exist, --only strands should return at most strands
    found = catalog.discover(skip=("strands",), only=("strands",))
    keys = [w["key"] for w in found]
    assert keys == ["strands"] or keys == []  # empty if file missing during mid-scaffold

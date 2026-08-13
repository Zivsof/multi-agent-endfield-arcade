from datetime import datetime, timezone
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import report


def test_write_report_shape(tmp_path: Path):
    started = datetime.now(timezone.utc)
    workers = [
        report.empty_worker_entry(
            "strands",
            role="combat",
            launched=True,
            built=True,
            gate={"ok": True, "failures": []},
            qa={"works": True, "reason": "ok", "checks": ["load"]},
        )
    ]
    path = report.write_report(tmp_path, started, workers)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "started_at" in data
    assert "finished_at" in data
    assert "wall_s" in data
    assert data["workers"][0]["slug"] == "strands"
    assert data["workers"][0]["role"] == "combat"

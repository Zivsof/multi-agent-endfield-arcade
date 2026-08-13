"""Write ``site/run_report.json`` at end of a run (Step 11).

Always runs from ``agent.run`` after the ADK loop and ``_ensure_site``, even if the
orchestrator crashed early — so you still get a machine-readable summary of who
launched, gate/QA results, repairs, and ``disk_only`` siblings.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def write_report(site_dir: Path, started_at: datetime, workers: list[dict[str, Any]]) -> Path:
    """Serialize wall-clock timing + per-worker entries to ``site/run_report.json``."""
    finished = datetime.now(timezone.utc)
    wall = (finished - started_at).total_seconds()
    payload = {
        "started_at": started_at.isoformat(),
        "finished_at": finished.isoformat(),
        "wall_s": round(wall, 2),
        "workers": workers,
    }
    path = site_dir / "run_report.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def empty_worker_entry(slug: str, role: str = "", **extra: Any) -> dict[str, Any]:
    """Blank report row created when ``Team`` is constructed (filled during the run)."""
    base = {
        "slug": slug,
        "role": role,
        "objective": "",
        "launched": False,
        "exit_code": None,
        "duration_s": None,
        "built": False,
        "gate": None,
        "qa": None,
        "repaired": False,
        "log": f"logs/{slug}.log",
        "disk_only": False,
    }
    base.update(extra)
    return base

"""In-memory scan-progress registry.

A long DAST scan publishes its current position (which entry point, N of M) here,
keyed by the scanned object's uuid. The plugin's ``GET /scan-status`` endpoint
reads it so the UI can show a live "now processing …" label while the POST is in
flight. Process-local and best-effort — purely for UX, never load-bearing.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, Optional

_LOCK = threading.Lock()
_PROGRESS: Dict[str, Dict[str, Any]] = {}


def start(uuid: str, total: int) -> None:
    with _LOCK:
        _PROGRESS[uuid] = {
            "state": "running",
            "total": total,
            "current": 0,
            "entry_point": None,
        }


def update(
    uuid: str, *, current: int, entry_point: str, total: Optional[int] = None
) -> None:
    with _LOCK:
        p = _PROGRESS.get(uuid)
        if p is None:
            p = {"state": "running", "total": total or 0, "current": 0}
            _PROGRESS[uuid] = p
        p["current"] = current
        p["entry_point"] = entry_point
        if total is not None:
            p["total"] = total
        p["state"] = "running"


def finish(uuid: str) -> None:
    with _LOCK:
        p = _PROGRESS.get(uuid)
        if p is not None:
            p["state"] = "done"
            p["entry_point"] = None
            p["current"] = p.get("total", 0)


def get(uuid: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        p = _PROGRESS.get(uuid)
        return dict(p) if p is not None else None


def clear(uuid: str) -> None:
    with _LOCK:
        _PROGRESS.pop(uuid, None)

"""Persistent active-vMCP registry for the Simulate plugin (D3 / §4.6)."""
import json
import os
import threading
from typing import Dict, Optional


class ActiveVmcpRegistry:
    """skill_uuid -> {active: real|sim, real_vmcp_uuid, sim_vmcp_uuid}."""

    def __init__(self, path: str):
        self._path = path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._data: Dict[str, Dict[str, Optional[str]]] = self._load()

    def _load(self) -> Dict[str, Dict[str, Optional[str]]]:
        if not os.path.exists(self._path):
            return {}
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _flush(self) -> None:
        tmp = f"{self._path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)
        os.replace(tmp, self._path)

    def get(self, skill_uuid: str) -> Optional[Dict[str, Optional[str]]]:
        return self._data.get(skill_uuid)

    def upsert(self, skill_uuid: str, real_vmcp_uuid: str, sim_vmcp_uuid: Optional[str]) -> None:
        with self._lock:
            existing = self._data.get(skill_uuid, {})
            self._data[skill_uuid] = {
                "active": existing.get("active", "real"),
                "real_vmcp_uuid": real_vmcp_uuid,
                "sim_vmcp_uuid": sim_vmcp_uuid,
            }
            self._flush()

    def set_active(self, skill_uuid: str, active: str) -> None:
        if active not in ("real", "sim"):
            raise ValueError(f"invalid active value: {active}")
        with self._lock:
            entry = self._data.get(skill_uuid)
            if entry is None:
                raise KeyError(skill_uuid)
            if active == "sim" and not entry.get("sim_vmcp_uuid"):
                raise ValueError("cannot activate sim: no simulated vMCP for this skill")
            entry["active"] = active
            self._flush()

    def toggle(self, skill_uuid: str) -> str:
        entry = self._data.get(skill_uuid)
        if entry is None:
            raise KeyError(skill_uuid)
        new_active = "sim" if entry.get("active") == "real" else "real"
        self.set_active(skill_uuid, new_active)
        return new_active

    def active_vmcp_uuid(self, skill_uuid: str) -> Optional[str]:
        entry = self._data.get(skill_uuid)
        if entry is None:
            return None
        return entry["real_vmcp_uuid"] if entry["active"] == "real" else entry["sim_vmcp_uuid"]

    def remove(self, skill_uuid: str) -> None:
        with self._lock:
            self._data.pop(skill_uuid, None)
            self._flush()

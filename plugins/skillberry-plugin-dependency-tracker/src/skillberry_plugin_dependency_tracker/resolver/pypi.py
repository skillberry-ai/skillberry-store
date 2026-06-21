"""Best-effort, time-boxed PyPI enrichment.

Local resolution is the source of truth; this layer *adds* the canonical
published artifact sha256 and an "update available" signal from the PyPI JSON
API. It is strictly best-effort: any failure (rate-limit 429, timeout, offline,
404) becomes a per-package ``status`` and never raises — a scan must succeed even
when PyPI is unreachable (CI has hit 429s).

Enablement is env-gated: ``DEPENDENCY_TRACKER_PYPI=off`` (or ``0``/``false``)
disables enrichment entirely.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import requests

from .base import (
    PYPI_ERROR,
    PYPI_NOT_FOUND,
    PYPI_OK,
    PYPI_SKIPPED,
    PYPI_TIMEOUT,
    DependencyReport,
)

logger = logging.getLogger(__name__)

PYPI_URL = "https://pypi.org/pypi/{dist}/json"
DEFAULT_TIMEOUT = 3.0


def pypi_enabled_from_env() -> bool:
    """Default enrichment on; disabled by DEPENDENCY_TRACKER_PYPI in {0,off,false,no}."""
    val = os.getenv("DEPENDENCY_TRACKER_PYPI")
    if val is None:
        return True
    return val.strip().lower() not in ("0", "off", "false", "no")


def _version_gt(latest: Optional[str], local: Optional[str]) -> bool:
    """True when ``latest`` is a newer release than ``local`` (PEP 440 if available)."""
    if not latest or not local:
        return False
    try:
        from packaging.version import parse as _parse  # optional dep

        return _parse(latest) > _parse(local)
    except Exception:
        # Fallback: a plain inequality is a weak but safe signal.
        return latest != local


def _extract_artifact_hashes(data: Dict[str, Any]) -> Dict[str, str]:
    """Pull sdist + wheel sha256 from a PyPI ``/json`` payload's ``urls`` block."""
    out: Dict[str, str] = {}
    for entry in data.get("urls") or []:
        ptype = entry.get("packagetype")
        sha = (entry.get("digests") or {}).get("sha256")
        if not sha:
            continue
        if ptype == "sdist" and "sdist" not in out:
            out["sdist"] = sha
        elif ptype == "bdist_wheel" and "wheel" not in out:
            out["wheel"] = sha
    return out


def enrich_from_pypi(
    dist: str,
    local_version: Optional[str],
    *,
    timeout: float = DEFAULT_TIMEOUT,
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    """Return a pypi block for one distribution. Never raises."""
    getter = session.get if session is not None else requests.get
    try:
        resp = getter(PYPI_URL.format(dist=dist), timeout=timeout)
    except requests.Timeout:
        return {"status": PYPI_TIMEOUT}
    except requests.RequestException as e:
        logger.debug("pypi enrich failed for %s: %s", dist, e)
        return {"status": PYPI_ERROR}

    if resp.status_code == 404:
        return {"status": PYPI_NOT_FOUND}
    if resp.status_code != 200:
        # 429 and friends land here — best-effort, treat as a soft error.
        return {"status": PYPI_ERROR}

    try:
        data = resp.json()
    except ValueError:
        return {"status": PYPI_ERROR}

    latest = (data.get("info") or {}).get("version")
    return {
        "status": PYPI_OK,
        "latest_version": latest,
        "update_available": _version_gt(latest, local_version),
        "artifact_sha256": _extract_artifact_hashes(data),
    }


def enrich_report(
    report: DependencyReport,
    *,
    enabled: bool = True,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """Enrich every package in ``report`` in place. Returns rolled-up status.

    When ``enabled`` is False, leaves every ``pypi`` as None and returns
    ``skipped``. Reuses a single :class:`requests.Session` for connection reuse.
    """
    if not enabled:
        return PYPI_SKIPPED

    session = requests.Session()
    try:
        for name in sorted(report.packages):
            pkg = report.packages[name]
            if pkg.version is None:
                # Nothing locally resolved; don't attribute a pypi block.
                continue
            pkg.pypi = enrich_from_pypi(
                pkg.name, pkg.version, timeout=timeout, session=session
            )
    finally:
        session.close()
    return report._pypi_status()

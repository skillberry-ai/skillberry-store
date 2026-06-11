"""Bandit SAST engine.

Wraps the `bandit` CLI (https://github.com/PyCQA/bandit), a static analyzer for
Python. We invoke it as a subprocess with JSON output rather than via its Python
API, because the JSON contract is stable across versions and isolates us from
bandit internals.
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from typing import List, Optional

from .base import (
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    Finding,
    SastEngine,
)

logger = logging.getLogger(__name__)

# bandit's issue_severity values -> our normalized ladder. bandit has no
# "critical"; HIGH is its top severity.
_SEVERITY_MAP = {
    "LOW": SEVERITY_LOW,
    "MEDIUM": SEVERITY_MEDIUM,
    "HIGH": SEVERITY_HIGH,
}

# bandit returns exit code 1 when it finds issues; >1 means a real error.
_BANDIT_RUN_ERROR = 2

_SCAN_TIMEOUT_SECONDS = 120


def parse_bandit_json(raw: str) -> List[Finding]:
    """Parse bandit's JSON report into normalized findings.

    Standalone (no bandit needed) so it can be unit-tested against a captured
    report. A report with no ``results`` yields an empty list.
    """
    data = json.loads(raw)
    findings: List[Finding] = []
    for result in data.get("results") or []:
        severity = _SEVERITY_MAP.get(
            str(result.get("issue_severity", "")).upper(), SEVERITY_MEDIUM
        )
        findings.append(
            Finding(
                engine=BanditEngine.name,
                rule_id=result.get("test_id") or result.get("test_name") or "bandit",
                severity=severity,
                message=result.get("issue_text") or "",
                line=result.get("line_number"),
                snippet=(result.get("code") or "").strip() or None,
            )
        )
    return findings


def _find_bandit() -> Optional[str]:
    """Locate the bandit executable.

    Checks PATH first, then the bin/Scripts dir next to the running Python
    interpreter. The latter matters because a server launched via
    ``python -m ...`` does not necessarily have the venv's bin dir on PATH,
    yet bandit (installed as a console script) lives right beside ``python``.
    """
    found = shutil.which("bandit")
    if found:
        return found
    bindir = os.path.dirname(sys.executable)
    for candidate in ("bandit", "bandit.exe"):
        path = os.path.join(bindir, candidate)
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


class BanditEngine(SastEngine):
    """Run Bandit over a single Python source blob."""

    name = "bandit"
    languages = ("python", "py")

    def is_available(self) -> bool:
        return _find_bandit() is not None

    def scan(
        self, code: str, *, filename: str, language: Optional[str] = None
    ) -> List[Finding]:
        # bandit scans files, so write the blob to a temp .py file. Suffix is
        # forced to .py regardless of the source filename so bandit treats it
        # as Python.
        bandit_exe = _find_bandit()
        if bandit_exe is None:
            raise RuntimeError("bandit is not installed")

        tmp_path: Optional[str] = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as fh:
                fh.write(code)
                tmp_path = fh.name

            proc = subprocess.run(
                [bandit_exe, "-f", "json", "-q", tmp_path],
                capture_output=True,
                text=True,
                timeout=_SCAN_TIMEOUT_SECONDS,
            )
        except FileNotFoundError:
            # `bandit` vanished between is_available() and here.
            raise RuntimeError("bandit is not installed")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"bandit scan timed out after {_SCAN_TIMEOUT_SECONDS}s")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError as e:  # pragma: no cover - best effort cleanup
                    logger.debug("Could not remove temp file %s: %s", tmp_path, e)

        # Exit code 1 == issues found (expected). >=2 == bandit error.
        if proc.returncode >= _BANDIT_RUN_ERROR:
            raise RuntimeError(
                f"bandit failed (exit {proc.returncode}): {proc.stderr.strip()}"
            )

        if not proc.stdout.strip():
            return []
        try:
            return parse_bandit_json(proc.stdout)
        except (ValueError, json.JSONDecodeError) as e:
            raise RuntimeError(f"could not parse bandit output: {e}")

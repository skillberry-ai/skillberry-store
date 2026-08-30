# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0
"""Guards that the dead ``ENABLE_UI`` switch stays deleted.

Background (PR #308 review, issue #8): once the UI moved into FastAPI, ``main()``
read only ``ENABLE_UI_SUBPROCESS`` and ``ENABLE_UI`` was consulted nowhere — so
setting it to ``false`` silently still served the UI, while the README, the
configuration guide and the website all documented it as a working switch. Of the
two options offered by the review (wire it up, or delete it everywhere), this
repo deletes it: the bundle is served in-process at ``/ui`` and there is no
supported API-only mode.

Related: issue #14 — conftest.py set ``ENABLE_UI=false``, implying API-only test
coverage that never existed.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[3]

# ENABLE_UI_SUBPROCESS is a different, live switch (restores the old `vite
# preview` subprocess), so match ENABLE_UI only when not followed by an underscore.
ENABLE_UI = re.compile(r"\bENABLE_UI(?!_)")

# Files that necessarily name the switch in order to describe its removal:
# the triage document, and this guard itself.
EXEMPT = {
    "docs/feedback_308.md",
    "src/skillberry_store/tests/test_enable_ui_switch_removed.py",
}

TEXT_SUFFIXES = {
    ".py", ".md", ".ts", ".tsx", ".js", ".jsx", ".html", ".yaml", ".yml",
    ".mk", ".toml", ".cfg", ".ini", ".sh", ".txt", ".json",
}


def _tracked_text_files() -> list[Path]:
    """Files tracked by git — avoids node_modules, dist and other build output."""
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    ).stdout
    names = [n for n in out.split("\0") if n]
    return [
        REPO_ROOT / n
        for n in names
        if n not in EXEMPT
        and (Path(n).suffix in TEXT_SUFFIXES or Path(n).name in ("Makefile", "Dockerfile"))
    ]


def test_enable_ui_is_not_referenced_anywhere():
    """Neither code nor docs may mention a switch that does nothing."""
    offenders = []
    for path in _tracked_text_files():
        try:
            text = path.read_text()
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if ENABLE_UI.search(line):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {line.strip()}")
    assert not offenders, (
        "ENABLE_UI was deleted (there is no API-only mode); these references "
        "document or set a switch that does nothing:\n" + "\n".join(offenders)
    )
    # conftest.py is tracked, so this also covers issue #14: the test setup no
    # longer sets ENABLE_UI=false and no longer implies API-only coverage.


def test_ui_is_served_regardless_of_the_removed_switch(tmp_path, monkeypatch):
    """The deletion is deliberate: ENABLE_UI=false must not be expected to work.

    Pinning the behaviour keeps the decision explicit — a future reader seeing
    the variable in an old deployment manifest can find out here that it is inert
    rather than assuming it still gates the mount.
    """
    from skillberry_store.fast_api import server as server_module
    from skillberry_store.fast_api.server import SBS
    from skillberry_store.modules import object_handler
    from skillberry_store.services import registry
    from skillberry_store.tests.utils import clean_test_tmp_dir

    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><html><body>ui</body></html>")
    monkeypatch.setattr(server_module, "ui_dist_dir", lambda: dist)
    monkeypatch.setenv("ENABLE_UI", "false")

    clean_test_tmp_dir()
    object_handler.clear_object_handlers()
    registry.clear_services()
    try:
        with TestClient(SBS()) as client:
            assert client.get("/ui/index.html").status_code == 200
            assert client.get("/", follow_redirects=False).headers["location"] == "/ui/"
    finally:
        object_handler.clear_object_handlers()
        registry.clear_services()

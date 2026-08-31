# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0
"""Guards the user-facing docs against the pre-#308 UI model.

Background (PR #308 review, issue #13): the UI moved from a separate `vite
preview` process on its own port to being served in-process by FastAPI at ``/ui``,
but README.md, docs/config-env-vars.md and site/getting-started.html still told
users to open port 3000 (or 8002) and to configure a switch that no longer exists.
Users configured a no-op switch and a dead port.

The port numbers themselves are not wrong everywhere — ``make ui-dev`` still runs
Vite on 8002 — so these tests check that any surviving mention is scoped to the
dev server, and that the documented way to reach the UI is the real one.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs" / "config-env-vars.md",
    REPO_ROOT / "site" / "getting-started.html",
]

# The port the pre-#308 UIManager default used; nothing serves it any more.
DEAD_PORT = re.compile(r"\b(?:localhost|127\.0\.0\.1|0\.0\.0\.0):3000\b|\bport `?3000`?")
# A UI URL on a port of its own, e.g. http://localhost:8002 (with no /ui path).
UI_ON_OWN_PORT = re.compile(r"https?://[\w.]+:8002(?![\w/])")
# Mentions of 8002 must be scoped to the dev server / legacy subprocess.
DEV_SERVER_CONTEXT = ("ui-dev", "vite", "dev server", "ENABLE_UI_SUBPROCESS")


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: p.name)
def test_docs_do_not_reference_the_dead_ui_port(doc):
    offenders = [
        f"{doc.name}:{n}: {line.strip()}"
        for n, line in enumerate(doc.read_text().splitlines(), start=1)
        if DEAD_PORT.search(line)
    ]
    assert not offenders, (
        "port 3000 predates #308 and nothing serves it:\n" + "\n".join(offenders)
    )


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: p.name)
def test_docs_do_not_send_users_to_a_standalone_ui_url(doc):
    offenders = [
        f"{doc.name}:{n}: {line.strip()}"
        for n, line in enumerate(doc.read_text().splitlines(), start=1)
        if UI_ON_OWN_PORT.search(line)
    ]
    assert not offenders, (
        "the UI is served at /ui on the API port, not on a port of its own:\n"
        + "\n".join(offenders)
    )


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: p.name)
def test_surviving_8002_mentions_are_scoped_to_the_dev_server(doc):
    """`make ui-dev` legitimately uses 8002 — but say so on the same line."""
    offenders = [
        f"{doc.name}:{n}: {line.strip()}"
        for n, line in enumerate(doc.read_text().splitlines(), start=1)
        if "8002" in line
        and not any(marker.lower() in line.lower() for marker in DEV_SERVER_CONTEXT)
    ]
    assert not offenders, (
        "an unqualified 8002 reads as the way to reach the UI; scope it to the "
        "Vite dev server or the legacy subprocess:\n" + "\n".join(offenders)
    )


def test_readme_documents_the_real_ui_url():
    readme = (REPO_ROOT / "README.md").read_text()

    assert "http://localhost:8000/ui/" in readme, (
        "the README must point users at the URL the backend actually serves"
    )


def test_getting_started_documents_the_real_ui_url():
    page = (REPO_ROOT / "site" / "getting-started.html").read_text()

    assert "http://localhost:8000/ui/" in page


def test_config_guide_scopes_the_legacy_ui_port_variable():
    """SBS_UI_PORT only feeds the legacy subprocess; VITE_UI_PORT feeds `make ui-dev`."""
    guide = (REPO_ROOT / "docs" / "config-env-vars.md").read_text()

    sbs_ui_port_rows = [line for line in guide.splitlines() if "`SBS_UI_PORT`" in line]
    assert sbs_ui_port_rows, "SBS_UI_PORT should still be documented, but scoped"
    for row in sbs_ui_port_rows:
        assert "ENABLE_UI_SUBPROCESS" in row, (
            "SBS_UI_PORT no longer controls the UI users reach; say which mode it "
            f"applies to: {row.strip()}"
        )
    assert "`VITE_UI_PORT`" in guide, (
        "the port `make ui-dev` actually honours should be documented"
    )

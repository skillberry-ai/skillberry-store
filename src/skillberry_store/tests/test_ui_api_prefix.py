# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0
"""Static guards keeping the UI free of the dead "/api" URL prefix.

Background (PR #308 review, issue #1): the UI used to be served by `vite preview`
with a proxy that rewrote "/api/*" onto the FastAPI routes. That proxy is gone —
the bundle is now served in-process by FastAPI — so any URL that still carries
the "/api" prefix 404s at runtime. Plugin-declared endpoints keep the legacy
prefix for backwards compatibility and are stripped by
`ui/src/utils/endpoints.ts::normalizeEndpoint`, which must be applied at *every*
raw `fetch()` of a plugin-supplied URL.

These are static (source-scanning) tests on purpose: the vitest suite that would
otherwise cover this is not run by any CI workflow, so `make test` is the only
gate that sees a regression here.
"""

from __future__ import annotations

import re
from pathlib import Path

UI_SRC = Path(__file__).resolve().parents[1] / "ui" / "src"

# The normaliser itself and its unit test necessarily name the prefix they strip.
EXEMPT = {
    UI_SRC / "utils" / "endpoints.ts",
    UI_SRC / "utils" / "endpoints.test.ts",
}

# Components that fetch plugin-declared (i.e. externally supplied) URLs. Every
# fetch in these files must route through normalizeEndpoint.
PLUGIN_DRIVEN = [
    UI_SRC / "components" / "PluginActionForm.tsx",
    UI_SRC / "components" / "PluginNotifications.tsx",
    UI_SRC / "components" / "CatalogImportView.tsx",
]

# A URL literal starting with /api — in single, double or back quotes.
API_URL_LITERAL = re.compile(r"""['"`]/api(?:/|['"`])""")

# `fetch(<expr>` — capture enough of the argument to classify it.
FETCH_CALL = re.compile(r"\bfetch\(\s*([^,)]*)")

# `const <name> = ... normalizeEndpoint(` — an identifier holding a normalised URL.
NORMALIZED_VAR = re.compile(r"\b(?:const|let|var)\s+(\w+)\s*(?::[^=]+)?=\s*normalizeEndpoint\(")


def _ui_sources(include_tests: bool = False) -> list[Path]:
    files = [
        p
        for p in UI_SRC.rglob("*")
        if p.suffix in (".ts", ".tsx") and p.is_file() and p not in EXEMPT
    ]
    if not include_tests:
        files = [p for p in files if ".test." not in p.name and "/test/" not in p.as_posix()]
    assert files, f"no UI sources found under {UI_SRC}"
    return files


def test_no_api_prefixed_url_literals_in_ui_sources():
    """No production UI source may hardcode an "/api"-prefixed URL."""
    offenders = []
    for path in _ui_sources():
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            if API_URL_LITERAL.search(line):
                offenders.append(f"{path.relative_to(UI_SRC)}:{lineno}: {line.strip()}")
    assert not offenders, (
        "UI sources still contain /api-prefixed URL literals; the Vite rewrite "
        "proxy no longer exists, so these 404 at runtime:\n" + "\n".join(offenders)
    )


def test_plugin_driven_fetches_are_normalized():
    """Every raw fetch of a plugin-declared URL goes through normalizeEndpoint."""
    offenders = []
    for path in PLUGIN_DRIVEN:
        text = path.read_text()
        assert "normalizeEndpoint" in text, f"{path.name} does not import the normaliser"
        normalized_vars = set(NORMALIZED_VAR.findall(text))
        for match in FETCH_CALL.finditer(text):
            arg = match.group(1).strip()
            if arg.startswith("normalizeEndpoint(") or arg in normalized_vars:
                continue
            lineno = text.count("\n", 0, match.start()) + 1
            offenders.append(f"{path.relative_to(UI_SRC)}:{lineno}: fetch({arg}...)")
    assert not offenders, (
        "these fetch() sites bypass normalizeEndpoint, so a plugin-declared "
        '"/api/..." endpoint would 404:\n' + "\n".join(offenders)
    )


def test_normalizer_is_shared_and_not_duplicated():
    """The normaliser lives in one shared module, not copied per component."""
    shared = UI_SRC / "utils" / "endpoints.ts"
    assert shared.is_file(), f"missing shared module {shared}"
    assert "export function normalizeEndpoint" in shared.read_text()

    duplicates = [
        str(p.relative_to(UI_SRC))
        for p in _ui_sources(include_tests=True)
        if re.search(r"function\s+normalizeEndpoint\b", p.read_text())
    ]
    assert not duplicates, f"normalizeEndpoint re-declared outside the shared module: {duplicates}"

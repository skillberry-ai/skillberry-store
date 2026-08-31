# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0
"""Guards that production UI builds do not publish the frontend source.

Background (PR #308 review, issue #5): `GET /ui*`, `HEAD /ui*` and `GET /` are on
the unauthenticated allow-list and the bundle is served in-process by FastAPI on
the *same* port as the API, so it can no longer be firewalled separately the way
the old port-8002 `vite preview` could. `vite.config.ts` kept
`build.sourcemap: true`, so every deployment also shipped the complete original
TypeScript to anyone who could reach the service.

Sourcemaps are now opt-in via `VITE_SOURCEMAP` (`true` / `1` / `yes`).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
UI_DIR = REPO_ROOT / "src" / "skillberry_store" / "ui"
VITE_CONFIG = UI_DIR / "vite.config.ts"
OPT_IN_ENV = "VITE_SOURCEMAP"


def _build_block() -> str:
    """The `build: { ... }` block of vite.config.ts."""
    match = re.search(r"\n  build:\s*\{(.*?)\n  \},", VITE_CONFIG.read_text(), re.DOTALL)
    assert match, "could not locate the build block in vite.config.ts"
    return match.group(1)


def test_sourcemaps_are_not_unconditionally_enabled():
    setting = re.search(r"sourcemap:\s*([^,\n]+)", _build_block())
    assert setting, "vite.config.ts declares no build.sourcemap setting"
    value = setting.group(1).strip()
    assert value != "true", (
        "build.sourcemap is hardcoded to true, so every production bundle ships "
        "the original TypeScript on the same unauthenticated port as the API"
    )
    assert OPT_IN_ENV in VITE_CONFIG.read_text(), (
        f"sourcemaps should be gated on {OPT_IN_ENV} so they can still be enabled "
        "deliberately when debugging a deployed build"
    )


def test_sourcemap_opt_in_accepts_documented_values():
    """The gate must recognise the values the comment tells operators to use."""
    helper = re.search(
        r"function sourcemapsEnabled\(\)[^{]*\{(.*?)\n\}", VITE_CONFIG.read_text(), re.DOTALL
    )
    assert helper, "no sourcemapsEnabled() helper in vite.config.ts"
    body = helper.group(1)
    assert f"process.env.{OPT_IN_ENV}" in body
    for accepted in ("'true'", "'1'", "'yes'"):
        assert accepted in body, f"{accepted} should be accepted as an opt-in value"


@pytest.mark.skipif(
    os.environ.get(OPT_IN_ENV, "").strip().lower() in ("true", "1", "yes"),
    reason=f"{OPT_IN_ENV} is set: sourcemaps were requested deliberately",
)
def test_built_bundle_ships_no_sourcemaps():
    """If a bundle has been built without the opt-in, it must carry no .map files."""
    dist = UI_DIR / "dist"
    if not dist.exists():
        pytest.skip("UI bundle not built (run `make ui-build`)")

    maps = sorted(str(p.relative_to(dist)) for p in dist.rglob("*.map"))
    assert not maps, (
        "the built bundle contains sourcemaps, which /ui serves unauthenticated: "
        f"{maps}. Rebuild without {OPT_IN_ENV} set."
    )

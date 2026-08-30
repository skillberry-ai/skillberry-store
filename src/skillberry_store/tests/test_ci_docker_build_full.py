# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0
"""Guards that CI actually builds and pushes the all-plugins ("-full") image.

Background (PR #308 review, issue #2): the default image became core-only and a
`docker-build-full` target was added for the companion all-plugins variant — but
nothing ever called it. `ci-push` in skillberry-common only runs `docker-build`,
so `:<version>-full` / `:latest-full` — the tags the BREAKING migration note
tells deployments to switch to — would never exist in the registry.

A target with no caller is exactly what these tests catch, so they assert the
wiring in make's own resolved database rather than by reading the makefiles.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
MAKEFILES = [
    REPO_ROOT / ".mk" / "dev.mk",
    REPO_ROOT / ".mk" / "local.mk",
    REPO_ROOT / ".mk" / "process.mk",
]

# The CI hook that must pull the -full variant into the push flow.
CI_FULL_TARGET = "ci-docker-build-full"

pytestmark = pytest.mark.skipif(
    shutil.which("make") is None, reason="make is not available on this host"
)


def _make_database() -> str:
    """Dump make's resolved rule database without running any recipe."""
    proc = subprocess.run(
        ["make", "-pRrq", "ci-push"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    # -q exits 1 when targets are out of date (always true for .PHONY targets);
    # the database is still printed. Only a missing database is a failure.
    assert "# Files" in proc.stdout, f"could not read make database:\n{proc.stderr}"
    return proc.stdout


def _prerequisites(database: str, target: str) -> list[str]:
    match = re.search(rf"^{re.escape(target)}:(.*)$", database, re.MULTILINE)
    assert match, f"target {target!r} is not defined in the make database"
    return match.group(1).split()


@pytest.fixture(scope="module")
def database() -> str:
    return _make_database()


def test_ci_push_builds_the_full_image_variant(database: str):
    """`make ci-push` must reach the -full build; a target with no caller is the bug."""
    assert CI_FULL_TARGET in _prerequisites(database, "ci-push"), (
        f"ci-push does not depend on {CI_FULL_TARGET}, so :latest-full would "
        "never be pushed to the registry"
    )


def test_full_image_is_pushed_only_after_lint_and_tests(database: str):
    """The -full push must be gated behind ci-pull-request (lint + test + e2e)."""
    assert "ci-pull-request" in _prerequisites(database, CI_FULL_TARGET), (
        f"{CI_FULL_TARGET} must depend on ci-pull-request so no image is pushed "
        "from a commit that failed lint/test/test-e2e"
    )


def test_ci_hook_pushes_to_the_registry_and_delegates_to_docker_build_full():
    """The hook must set DBT=registry (push, not a throwaway local build)."""
    dev_mk = (REPO_ROOT / ".mk" / "dev.mk").read_text()
    recipe = re.search(
        rf"^{re.escape(CI_FULL_TARGET)}:.*?\n((?:\t.*\n)+)", dev_mk, re.MULTILINE
    )
    assert recipe, f"{CI_FULL_TARGET} has no recipe in .mk/dev.mk"
    body = recipe.group(1)
    assert "DBT=registry" in body, "the CI -full build must push, i.e. set DBT=registry"
    assert "docker-build-full" in body, "the CI hook must delegate to docker-build-full"


def test_docker_build_full_tags_and_bundles_all_plugins():
    """The -full variant is only meaningful with the suffix and the plugin extra."""
    dev_mk = (REPO_ROOT / ".mk" / "dev.mk").read_text()
    recipe = re.search(r"^docker-build-full:.*?\n((?:\t.*\n)+)", dev_mk, re.MULTILINE)
    assert recipe, "docker-build-full has no recipe in .mk/dev.mk"
    body = recipe.group(1)
    assert "IMAGE_TAG_SUFFIX=-full" in body
    assert "PLUGIN_EXTRAS=plugins-all" in body


@pytest.mark.parametrize("target", ["docker-build-full", CI_FULL_TARGET])
def test_full_image_targets_are_self_documented(target: str):
    """`make help` only lists targets carrying a `##` comment on the same line."""
    for makefile in MAKEFILES:
        for line in makefile.read_text().splitlines():
            if re.match(rf"^{re.escape(target)}:", line):
                if "##" in line:
                    return
                pytest.fail(
                    f"{target} is defined in {makefile.name} without a `##` "
                    "comment on the same line, so `make help` omits it"
                )
    pytest.fail(f"{target} is not defined in any of {[m.name for m in MAKEFILES]}")

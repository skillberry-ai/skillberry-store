# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0
"""Guards that SDK generation installs the toolchain it invokes.

Background (PR #308 review, issue #4): openapi-generator-cli,
openapi-python-client and toml-cli moved into the new ``[build]`` extra, but
``generate-sdk`` (skillberry-common/.mk/dev.mk) depends on
``install-requirements`` with an unset ``ODEPS`` — core dependencies only — and
nothing earlier installs ``[build]``. ``make update-sdk``, which ``ci-push``
runs, therefore fails with ``openapi-generator-cli: command not found``.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - the project floor is 3.11
    import tomli as tomllib

REPO_ROOT = Path(__file__).resolve().parents[3]
DEV_MK = REPO_ROOT / ".mk" / "dev.mk"

# Executables generate-sdk's recipe shells out to, and the extra that ships them.
GENERATE_SDK_TOOLS = {
    "openapi-generator-cli": "openapi-generator-cli",
    "toml": "toml-cli",
}
BUILD_EXTRA = "build"


def _make_prerequisites(target: str) -> list[str]:
    """Prerequisites of `target` from make's resolved database (no recipe runs)."""
    proc = subprocess.run(
        ["make", "-pRrq", target],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert "# Files" in proc.stdout, f"could not read make database:\n{proc.stderr}"
    match = re.search(rf"^{re.escape(target)}:(.*)$", proc.stdout, re.MULTILINE)
    assert match, f"target {target!r} is not defined in the make database"
    return match.group(1).split()


def _recipe(makefile_text: str, target: str) -> str:
    """The recipe body of `target`, or "" when it is defined elsewhere."""
    match = re.search(
        rf"^{re.escape(target)}:.*?\n((?:\t.*\n)+)", makefile_text, re.MULTILINE
    )
    return match.group(1) if match else ""


@pytest.mark.skipif(shutil.which("make") is None, reason="make is not available")
def test_generate_sdk_installs_the_build_extra():
    """generate-sdk must pull in a prerequisite that installs [build]."""
    prereqs = _make_prerequisites("generate-sdk")
    dev_mk = DEV_MK.read_text()

    installers = [p for p in prereqs if f"ODEPS={BUILD_EXTRA}" in _recipe(dev_mk, p)]
    assert installers, (
        "no prerequisite of generate-sdk installs the [build] extra "
        f"(prerequisites: {prereqs}), so its codegen tools are missing and "
        "`make update-sdk` fails with openapi-generator-cli: command not found"
    )


@pytest.mark.skipif(shutil.which("make") is None, reason="make is not available")
def test_build_extra_installer_uses_a_recursive_make():
    """The install stamp embeds $(ODEPS) at parse time, so ODEPS needs a fresh parse."""
    dev_mk = DEV_MK.read_text()
    body = _recipe(dev_mk, "install-build-requirements")
    assert body, "install-build-requirements has no recipe in .mk/dev.mk"
    assert "$(MAKE)" in body, (
        "must invoke a recursive $(MAKE) install-requirements: "
        ".stamps/install-requirements-$(ODEPS) expands ODEPS at parse time"
    )
    assert f"ODEPS={BUILD_EXTRA}" in body


@pytest.mark.parametrize("executable,package", sorted(GENERATE_SDK_TOOLS.items()))
def test_generate_sdk_tools_are_declared_in_the_build_extra(executable, package):
    """The tools the recipe shells out to must actually be in the extra we install."""
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    extra = pyproject["project"]["optional-dependencies"][BUILD_EXTRA]
    declared = {re.split(r"[\[><=!;]", req, maxsplit=1)[0].strip() for req in extra}
    assert package in declared, (
        f"{executable} is invoked by generate-sdk but {package} is not in the "
        f"[{BUILD_EXTRA}] extra"
    )

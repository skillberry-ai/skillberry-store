# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0
"""Guards the version bounds on the embedding dependency.

Background (PR #308 review, issue #11): ``fastembed`` had no version bound in
pyproject.toml while the model string is pinned in ``vector_db_interface.py``. A
major bump renaming or dropping ``sentence-transformers/all-MiniLM-L6-v2`` fails
at the first embed — in production, on a readiness probe — rather than at build
time. The truncation pin added for issue #10 also depends on the internal
``.model.tokenizer`` path, widening the surface an unrelated dependency bump can
break.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - the project floor is 3.11
    import tomli as tomllib

REPO_ROOT = Path(__file__).resolve().parents[4]
PACKAGE = "fastembed"


def _requirement(name: str) -> str:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    for requirement in pyproject["project"]["dependencies"]:
        if re.split(r"[\[><=!;\s]", requirement, maxsplit=1)[0].strip() == name:
            return requirement
    raise AssertionError(f"{name} is not a declared dependency")


def test_fastembed_has_a_lower_bound():
    """Without a floor, a resolver may pick a release predating the ONNX weights."""
    requirement = _requirement(PACKAGE)

    assert ">=" in requirement, (
        f"{PACKAGE} needs at least a lower bound: {requirement!r}"
    )


def test_fastembed_has_an_upper_bound():
    """Pre-1.0: minor releases are the breaking increments.

    We pin the model string and reach into `.model.tokenizer` (issue #10), so a
    minor bump must be an explicit, tested decision rather than something a
    resolver does silently.
    """
    requirement = _requirement(PACKAGE)

    assert "<" in requirement, (
        f"{PACKAGE} needs an upper bound so a breaking release cannot be picked "
        f"up silently: {requirement!r}"
    )


def test_installed_fastembed_satisfies_the_declared_bounds():
    """The declared range must match what the suite is actually validating."""
    from packaging.requirements import Requirement
    from packaging.version import Version

    import fastembed

    requirement = Requirement(_requirement(PACKAGE))
    installed = Version(fastembed.__version__)

    assert installed in requirement.specifier, (
        f"installed {PACKAGE} {installed} is outside the declared {requirement}"
    )


def test_pinned_model_still_resolves_in_the_installed_release():
    """The whole point of the bound: the pinned model name must still exist."""
    from fastembed import TextEmbedding

    from skillberry_store.vdbs.vector_db_interface import _ENCODER_MODEL

    available = {entry["model"] for entry in TextEmbedding.list_supported_models()}

    assert _ENCODER_MODEL in available, (
        f"{_ENCODER_MODEL} is no longer offered by this fastembed release; "
        "raising the upper bound requires re-checking the model string"
    )

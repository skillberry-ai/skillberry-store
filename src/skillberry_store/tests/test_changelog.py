# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0
"""Guards that breaking changes have a migration note deployers can find.

Background (PR #308 review, issue #16): the squash merge collapsed all 13 commit
messages, so the measurement data and the ``BREAKING:`` note lived only on the PR
page, and there was no CHANGELOG for the "call out in the release notes" TODO to
land in.

These tests are deliberately about *structure and the specific migrations*, not
prose: they check the file exists, is organised into releases with an Unreleased
section, and that the two breaking changes a deployer must act on are actually
documented with the identifier they would search for.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
CHANGELOG = REPO_ROOT / "CHANGELOG.md"


@pytest.fixture(scope="module")
def changelog() -> str:
    assert CHANGELOG.is_file(), (
        "CHANGELOG.md is missing: with squash merges, a breaking change has "
        "nowhere else to be communicated"
    )
    return CHANGELOG.read_text()


def test_has_an_unreleased_section(changelog):
    """Unmerged breaking changes need a home, or they end up only in a PR body."""
    assert re.search(r"^##\s+Unreleased", changelog, re.MULTILINE | re.IGNORECASE)


def test_has_at_least_one_released_section(changelog):
    releases = [
        line
        for line in changelog.splitlines()
        if line.startswith("## ") and "unreleased" not in line.lower()
    ]
    assert releases, "no released section — the #308 migration note has no home"


def test_marks_breaking_changes_explicitly(changelog):
    """A deployer scanning for what will break them needs a keyword to scan for."""
    assert re.search(r"^###\s+Breaking", changelog, re.MULTILINE), (
        "no Breaking subsection; breaking changes must be separated from ordinary ones"
    )


def test_documents_the_latest_full_migration(changelog):
    """The core-only default image is only actionable if the new tag is named."""
    assert ":latest-full" in changelog, (
        "the BREAKING note tells deployments to switch to :latest-full — the "
        "changelog must name that tag"
    )
    assert "docker-build-full" in changelog, (
        "name the target that builds the variant, so it can be built locally too"
    )
    assert "PLUGIN_EXTRAS" in changelog, (
        "deployments needing a subset of plugins need the build arg"
    )


def test_documents_the_removed_ui_switch(changelog):
    """Anything a deployer must delete from their config has to be named."""
    assert "ENABLE_UI" in changelog, "the removed switch must be named to be actionable"
    assert "ENABLE_UI_SUBPROCESS" in changelog, (
        "say explicitly that the similarly-named live switch is unaffected"
    )


def test_records_the_memory_measurements(changelog):
    """The measurements only existed on the PR page; that is what issue #16 is about."""
    assert re.search(r"812\s*MB", changelog), "the measured RSS figures should survive"

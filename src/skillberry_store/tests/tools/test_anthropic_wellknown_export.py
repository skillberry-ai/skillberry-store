"""Tests for the well-known agent-skills export layout."""

import json
from pathlib import Path

import pytest

from skillberry_store.tools.anthropic.exporter import (
    InvalidSkillNameError,
    WELLKNOWN_LEGACY_PREFIX,
    WELLKNOWN_PRIMARY_PREFIX,
    build_wellknown_index,
    export_skill_to_directory,
)


SKILL = {
    "name": "demo-skill",
    "description": "A demonstration skill for well-known export tests.",
}


def test_build_wellknown_index_shape() -> None:
    data = build_wellknown_index("my-skill", "Description of my skill.", ["SKILL.md"])
    payload = json.loads(data.decode("utf-8"))
    assert payload == {
        "skills": [
            {
                "description": "Description of my skill.",
                "files": ["SKILL.md"],
                "name": "my-skill",
            }
        ],
        "version": 1,
    }


def test_build_wellknown_index_is_deterministic() -> None:
    a = build_wellknown_index("s", "d", ["SKILL.md", "scripts/x.sh"])
    b = build_wellknown_index("s", "d", ["SKILL.md", "scripts/x.sh"])
    assert a == b


def test_export_directory_writes_top_level_and_wellknown(tmp_path: Path) -> None:
    export_skill_to_directory(
        skill=SKILL,
        tools=[],
        snippets=[],
        output_dir=str(tmp_path),
        npx_compat=True,
    )
    # Top-level SKILL.md preserved for existing WebDAV mount consumers.
    top = tmp_path / SKILL["name"] / "SKILL.md"
    assert top.exists(), "top-level SKILL.md missing"
    # Well-known primary + legacy copies.
    primary = tmp_path / WELLKNOWN_PRIMARY_PREFIX / SKILL["name"] / "SKILL.md"
    legacy = tmp_path / WELLKNOWN_LEGACY_PREFIX / SKILL["name"] / "SKILL.md"
    assert primary.exists()
    assert legacy.exists()
    # They must be byte-identical to the top-level copy.
    top_bytes = top.read_bytes()
    assert primary.read_bytes() == top_bytes
    assert legacy.read_bytes() == top_bytes


def test_export_directory_writes_index_json(tmp_path: Path) -> None:
    export_skill_to_directory(
        skill=SKILL,
        tools=[],
        snippets=[],
        output_dir=str(tmp_path),
        npx_compat=True,
    )
    primary_index = tmp_path / WELLKNOWN_PRIMARY_PREFIX / "index.json"
    legacy_index = tmp_path / WELLKNOWN_LEGACY_PREFIX / "index.json"
    assert primary_index.exists()
    assert legacy_index.exists()
    # Byte-identical primary and legacy manifests.
    assert primary_index.read_bytes() == legacy_index.read_bytes()

    payload = json.loads(primary_index.read_text("utf-8"))
    assert payload["version"] == 1
    assert len(payload["skills"]) == 1
    entry = payload["skills"][0]
    assert entry["name"] == SKILL["name"]
    assert entry["description"] == SKILL["description"]
    assert "SKILL.md" in entry["files"]


def test_index_files_matches_disk(tmp_path: Path) -> None:
    """Every file listed in index.json must exist on disk under the well-known path."""
    export_skill_to_directory(
        skill=SKILL,
        tools=[],
        snippets=[],
        output_dir=str(tmp_path),
        npx_compat=True,
    )
    payload = json.loads(
        (tmp_path / WELLKNOWN_PRIMARY_PREFIX / "index.json").read_text("utf-8")
    )
    for entry in payload["skills"]:
        for rel in entry["files"]:
            fetched = tmp_path / WELLKNOWN_PRIMARY_PREFIX / entry["name"] / rel
            assert fetched.exists(), f"advertised file missing: {rel}"


def test_export_directory_without_npx_compat_omits_wellknown(tmp_path: Path) -> None:
    export_skill_to_directory(
        skill=SKILL,
        tools=[],
        snippets=[],
        output_dir=str(tmp_path),
        npx_compat=False,
    )
    assert (tmp_path / SKILL["name"] / "SKILL.md").exists()
    assert not (tmp_path / ".well-known").exists()


def test_npx_compat_rejects_invalid_name(tmp_path: Path) -> None:
    """npx_compat=True validates the skill name as a slug."""
    with pytest.raises(InvalidSkillNameError):
        export_skill_to_directory(
            skill={"name": "My Skill", "description": "x"},
            tools=[],
            snippets=[],
            output_dir=str(tmp_path),
            npx_compat=True,
        )

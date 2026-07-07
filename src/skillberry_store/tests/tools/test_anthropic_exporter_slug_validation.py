"""Tests for slug validation in the Anthropic exporter API."""

import zipfile
import io

import pytest

from skillberry_store.tools.anthropic.exporter import (
    InvalidSkillNameError,
    export_skill_to_anthropic_format,
    export_skill_to_directory,
)


SKILL_INVALID = {
    "name": "My Skill",
    "description": "A test skill with a human-friendly name.",
}
SKILL_VALID = {
    "name": "my-skill",
    "description": "A test skill with a slug-safe name.",
}


def test_export_zip_strict_rejects_non_slug_name() -> None:
    with pytest.raises(InvalidSkillNameError) as info:
        export_skill_to_anthropic_format(SKILL_INVALID, tools=[], snippets=[])
    err = info.value
    assert err.name == "My Skill"
    assert err.suggested == "my-skill"
    assert err.reason


def test_export_zip_permissive_when_allow_invalid_name_true() -> None:
    payload = export_skill_to_anthropic_format(
        SKILL_INVALID, tools=[], snippets=[], allow_invalid_name=True
    )
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        names = zf.namelist()
    assert any("SKILL.md" in n for n in names)


def test_export_zip_accepts_valid_slug_by_default() -> None:
    payload = export_skill_to_anthropic_format(SKILL_VALID, tools=[], snippets=[])
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        names = zf.namelist()
    assert "my-skill/SKILL.md" in names


def test_export_directory_strict_rejects_non_slug_name(tmp_path) -> None:
    with pytest.raises(InvalidSkillNameError):
        export_skill_to_directory(
            SKILL_INVALID, tools=[], snippets=[], output_dir=str(tmp_path)
        )


def test_export_directory_permissive_when_allow_invalid_name_true(tmp_path) -> None:
    export_skill_to_directory(
        SKILL_INVALID,
        tools=[],
        snippets=[],
        output_dir=str(tmp_path),
        allow_invalid_name=True,
    )
    assert (tmp_path / "My Skill" / "SKILL.md").exists()

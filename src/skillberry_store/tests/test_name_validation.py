"""Unit tests for store name validation and slugification."""

import pytest
from fastapi import HTTPException

from skillberry_store.schemas.name_validation import (
    STORE_NAME_PATTERN,
    is_valid_store_name,
    slugify_store_name,
    validate_store_name,
)


@pytest.mark.parametrize(
    "name",
    [
        "docs-research",
        "context7",
        "pdf-to-markdown",
        "a",
        "1",
        "a" * 64,
    ],
)
def test_valid_store_names(name):
    assert is_valid_store_name(name)
    validate_store_name(name, kind="skill")


@pytest.mark.parametrize(
    "name",
    [
        "Test-Skill",
        "my_skill",
        "my skill",
        "my.skill",
        "my/skill",
        "",
        "a" * 65,
        None,
        123,
    ],
)
def test_invalid_store_names(name):
    assert not is_valid_store_name(name)
    with pytest.raises(HTTPException) as exc:
        validate_store_name(name, kind="skill")
    assert exc.value.status_code == 400
    detail = exc.value.detail
    assert isinstance(detail, dict)
    assert detail["error"] == "invalid_name"
    assert detail["kind"] == "skill"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Test_Anthropic_Skill", "test-anthropic-skill"),
        ("my skill", "my-skill"),
        ("my.skill.name", "my-skill-name"),
        ("UPPER", "upper"),
        ("  leading-trailing  ", "leading-trailing"),
        ("multiple___underscores", "multiple-underscores"),
        ("mixed_ _dots.and_spaces", "mixed-dots-and-spaces"),
    ],
)
def test_slugify_valid(raw, expected):
    assert slugify_store_name(raw) == expected
    assert is_valid_store_name(expected)


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "___",
        "!!!",
        None,
    ],
)
def test_slugify_unrecoverable_returns_none(raw):
    assert slugify_store_name(raw) is None


def test_store_name_pattern_matches_spec():
    assert STORE_NAME_PATTERN == r"^[a-z0-9-]{1,64}$"

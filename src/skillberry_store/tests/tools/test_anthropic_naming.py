"""Tests for the shared skill-slug validator."""

import pytest

from skillberry_store.tools.anthropic.naming import (
    SLUG_MAX_LEN,
    suggest_slug,
    validate_skill_slug,
)


@pytest.mark.parametrize(
    "name",
    ["a", "my-skill", "abc123", "web-design-guidelines", "x2y", "0-9"],
)
def test_valid_slugs(name: str) -> None:
    result = validate_skill_slug(name)
    assert result.ok is True
    assert result.suggested == name
    assert result.reason == ""


@pytest.mark.parametrize(
    "name,expected_suggested",
    [
        ("My Skill", "my-skill"),
        ("Web Design Guidelines", "web-design-guidelines"),
        ("Foo_Bar", "foo-bar"),
        ("UPPER", "upper"),
        ("has  spaces", "has-spaces"),
        ("trailing-", "trailing"),
        ("-leading", "leading"),
        ("weird!!chars??", "weird-chars"),
    ],
)
def test_invalid_names_produce_suggested_slug(name: str, expected_suggested: str) -> None:
    result = validate_skill_slug(name)
    assert result.ok is False
    assert result.suggested == expected_suggested
    assert result.reason


def test_empty_name_rejected() -> None:
    result = validate_skill_slug("")
    assert result.ok is False
    assert result.suggested == ""
    assert "empty" in result.reason.lower()


def test_none_name_rejected() -> None:
    result = validate_skill_slug(None)
    assert result.ok is False


def test_too_long_name_rejected_and_suggestion_truncated() -> None:
    long = "a" * (SLUG_MAX_LEN + 10)
    result = validate_skill_slug(long)
    assert result.ok is False
    assert len(result.suggested) <= SLUG_MAX_LEN


def test_suggest_slug_returns_empty_for_no_alphanumerics() -> None:
    assert suggest_slug("---") == ""
    assert suggest_slug("") == ""


def test_suggest_slug_does_not_leave_dangling_hyphens() -> None:
    assert not suggest_slug("!Hello World!").startswith("-")
    assert not suggest_slug("!Hello World!").endswith("-")

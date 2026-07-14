"""Unit tests for the field-selection helpers used by list endpoints."""

import pytest

from skillberry_store.services.field_selection import (
    SKILL_LIST_FIELDS,
    SNIPPET_LIST_FIELDS,
    TOOL_LIST_FIELDS,
    parse_fields_spec,
    select_item_fields,
    select_items_fields,
)


def test_parse_none_returns_none():
    assert parse_fields_spec(None, "snippet") is None
    assert parse_fields_spec("", "snippet") is None


def test_parse_full_returns_none():
    assert parse_fields_spec("full", "snippet") is None


def test_parse_list_returns_preset_copy():
    result = parse_fields_spec("list", "snippet")
    assert result == SNIPPET_LIST_FIELDS
    result.add("_scratch")
    assert "_scratch" not in SNIPPET_LIST_FIELDS


def test_parse_list_per_type():
    assert parse_fields_spec("list", "snippet") == SNIPPET_LIST_FIELDS
    assert parse_fields_spec("list", "tool") == TOOL_LIST_FIELDS
    assert parse_fields_spec("list", "skill") == SKILL_LIST_FIELDS


def test_parse_list_unknown_type_raises():
    with pytest.raises(ValueError, match="No list preset"):
        parse_fields_spec("list", "unknown")


def test_parse_csv_allowlist():
    assert parse_fields_spec("uuid,name", "snippet") == {"uuid", "name"}
    assert parse_fields_spec(" uuid , name , ", "snippet") == {"uuid", "name"}


def test_parse_csv_empty_string_falls_through_to_none():
    assert parse_fields_spec(",,,", "snippet") is None


def test_select_item_fields_none_returns_input_ref():
    item = {"uuid": "u1", "name": "n"}
    assert select_item_fields(item, None) is item


def test_select_item_fields_returns_fresh_dict_subset():
    item = {"uuid": "u1", "name": "n", "content": "big"}
    result = select_item_fields(item, {"uuid", "name"})
    assert result == {"uuid": "u1", "name": "n"}
    assert result is not item


def test_select_item_fields_ignores_missing_fields():
    item = {"uuid": "u1"}
    result = select_item_fields(item, {"uuid", "modified_at"})
    assert result == {"uuid": "u1"}


def test_select_item_fields_does_not_mutate_source():
    item = {"uuid": "u1", "name": "n", "content": "big"}
    select_item_fields(item, {"uuid"})
    assert item == {"uuid": "u1", "name": "n", "content": "big"}


def test_select_items_fields_shape():
    items = [{"uuid": "a", "content": "1"}, {"uuid": "b", "content": "2"}]
    result = select_items_fields(items, {"uuid"})
    assert result == [{"uuid": "a"}, {"uuid": "b"}]


def test_select_items_fields_none_returns_new_list_with_same_refs():
    items = [{"uuid": "a"}, {"uuid": "b"}]
    result = select_items_fields(items, None)
    assert result == items
    assert result is not items
    assert result[0] is items[0]


def test_snippet_preset_omits_content():
    assert "content" not in SNIPPET_LIST_FIELDS


def test_tool_preset_omits_heavy_fields():
    for k in ("params", "returns", "dependencies", "packaging_params"):
        assert k not in TOOL_LIST_FIELDS


def test_skill_preset_omits_populated_arrays():
    assert "tools" not in SKILL_LIST_FIELDS
    assert "snippets" not in SKILL_LIST_FIELDS
    assert "tool_uuids" in SKILL_LIST_FIELDS
    assert "snippet_uuids" in SKILL_LIST_FIELDS

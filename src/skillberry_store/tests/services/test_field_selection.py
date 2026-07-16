"""Unit tests for the field-selection helpers used by list endpoints."""

import pytest

from skillberry_store.services import field_selection as fs
from skillberry_store.services.field_selection import (
    SKILL_LIST_FIELDS,
    SNIPPET_LIST_FIELDS,
    TOOL_LIST_FIELDS,
    VMCP_LIST_FIELDS,
    VNFS_LIST_FIELDS,
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
    assert parse_fields_spec("list", "vmcp") == VMCP_LIST_FIELDS
    assert parse_fields_spec("list", "vnfs") == VNFS_LIST_FIELDS


def test_parse_list_unknown_type_raises():
    with pytest.raises(ValueError, match="No field tags registered"):
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


def test_vmcp_preset_keeps_runtime_status_fields():
    # The list UI depends on ``running`` / ``runtime`` — they must survive
    # the slim projection.
    assert "running" in VMCP_LIST_FIELDS
    assert "runtime" in VMCP_LIST_FIELDS


def test_vnfs_preset_keeps_runtime_status_fields():
    assert "running" in VNFS_LIST_FIELDS
    assert "export_path" in VNFS_LIST_FIELDS


# ── tag-based preset registry ─────────────────────────────────────────


def test_list_constants_match_tagged_fields_per_type():
    """The public ``*_LIST_FIELDS`` constants are computed views over the
    ``"list"`` tag of each type's field-tag table. Any drift (a field
    tagged ``"list"`` but missing from the constant, or vice-versa) is a
    bug in the registry."""
    assert SNIPPET_LIST_FIELDS == fs._fields_with_preset("snippet", "list")
    assert TOOL_LIST_FIELDS == fs._fields_with_preset("tool", "list")
    assert SKILL_LIST_FIELDS == fs._fields_with_preset("skill", "list")
    assert VMCP_LIST_FIELDS == fs._fields_with_preset("vmcp", "list")
    assert VNFS_LIST_FIELDS == fs._fields_with_preset("vnfs", "list")


def test_all_known_presets_currently_only_list():
    """Today the registry only declares the ``"list"`` preset. This test
    documents that invariant; adding a new preset should require an
    intentional update here."""
    assert fs._all_known_presets() == {"list"}


def test_field_can_carry_multiple_presets(monkeypatch):
    """Tagging a single field with more than one preset must resolve
    correctly for each preset independently — the core new-model
    invariant."""
    monkeypatch.setitem(
        fs._FIELD_TAGS_BY_TYPE,
        "snippet",
        {
            "uuid": {"list", "summary"},
            "name": {"list", "summary"},
            "description": {"list"},
            "content": set(),
        },
    )
    assert parse_fields_spec("list", "snippet") == {"uuid", "name", "description"}
    assert parse_fields_spec("summary", "snippet") == {"uuid", "name"}


def test_known_preset_undeclared_for_type_raises(monkeypatch):
    """If a preset name is declared for *some* type but no field of the
    target type carries it, requesting it must raise — no silent CSV
    fallback that would return ``{}`` per item."""
    # ``"summary"`` is declared for snippet but not for tool.
    monkeypatch.setitem(
        fs._FIELD_TAGS_BY_TYPE,
        "snippet",
        {"uuid": {"list", "summary"}, "name": {"list"}},
    )
    monkeypatch.setitem(
        fs._FIELD_TAGS_BY_TYPE,
        "tool",
        {"uuid": {"list"}, "name": {"list"}},
    )
    assert parse_fields_spec("summary", "snippet") == {"uuid"}
    with pytest.raises(ValueError, match="No 'summary' preset"):
        parse_fields_spec("summary", "tool")


def test_csv_still_supported_for_arbitrary_allowlist():
    """A caller-defined CSV must still resolve to the literal token set —
    the "unknown-preset-name" branch only triggers when the token is a
    registered preset name for some type."""
    assert parse_fields_spec("uuid,name,port", "vmcp") == {"uuid", "name", "port"}


def test_registered_preset_name_never_falls_through_to_csv(monkeypatch):
    """Backstop: a bare token that happens to be a known preset name must
    always take the preset path, never the CSV path — regardless of the
    caller's intent."""
    monkeypatch.setitem(
        fs._FIELD_TAGS_BY_TYPE,
        "snippet",
        {"uuid": {"list"}, "detail": {"list"}},
    )
    # ``"list"`` is a known preset — this must NOT parse as ``{"list"}``.
    assert parse_fields_spec("list", "snippet") == {"uuid", "detail"}

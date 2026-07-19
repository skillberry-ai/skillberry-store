"""Unit tests for the field-selection helpers used by list/search endpoints."""

import pytest

from skillberry_store.services import field_selection as fs
from skillberry_store.services.field_selection import (
    _FIELD_TAGS_BY_TYPE,
    _PRESET_NAMES,
    _PRESET_ORDER,
    parse_fields_spec,
    select_item_fields,
    select_items_fields,
    should_run_mechanism,
)


ALL_TYPES = ["snippet", "tool", "skill", "vmcp", "vnfs"]


# ── parse_fields_spec: default / full ────────────────────────────────


def test_parse_none_returns_narrow_allowlist():
    """The default preset is ``narrow`` — a missing ``fields_spec``
    resolves to the narrow allowlist for the type."""
    assert parse_fields_spec(None, "snippet") == fs._fields_with_preset(
        "snippet", "narrow"
    )


def test_parse_empty_returns_narrow_allowlist():
    """An empty query-string value is treated the same as omitted:
    resolves to the narrow allowlist."""
    assert parse_fields_spec("", "snippet") == fs._fields_with_preset(
        "snippet", "narrow"
    )


def test_parse_full_returns_full_allowlist():
    """``"full"`` resolves through the FieldTags like any other preset:
    the returned allowlist is exactly the fields tagged ``"full"`` for
    that type — which by convention covers every declared field,
    including the underscore-prefixed flag fields."""
    result = parse_fields_spec("full", "snippet")
    assert result == fs._fields_with_preset("snippet", "full")
    assert "content" in result  # payload field
    assert "modified_at" in result  # timestamp field


def test_parse_none_unknown_type_raises():
    with pytest.raises(ValueError, match="No field tags registered"):
        parse_fields_spec(None, "unknown")


def test_parse_full_unknown_type_raises():
    with pytest.raises(ValueError, match="No field tags registered"):
        parse_fields_spec("full", "unknown")


# ── parse_fields_spec: narrow / wide ─────────────────────────────────


def test_parse_minimal_returns_uuid_only_per_type():
    """``minimal`` is the identifier-only preset: exactly ``{"uuid"}``
    for every object type."""
    for t in ALL_TYPES:
        assert parse_fields_spec("minimal", t) == {"uuid"}


def test_parse_narrow_returns_narrow_set_per_type():
    assert parse_fields_spec("narrow", "snippet") == fs._fields_with_preset(
        "snippet", "narrow"
    )
    assert parse_fields_spec("narrow", "tool") == fs._fields_with_preset(
        "tool", "narrow"
    )
    assert parse_fields_spec("narrow", "skill") == fs._fields_with_preset(
        "skill", "narrow"
    )
    assert parse_fields_spec("narrow", "vmcp") == fs._fields_with_preset(
        "vmcp", "narrow"
    )
    assert parse_fields_spec("narrow", "vnfs") == fs._fields_with_preset(
        "vnfs", "narrow"
    )


def test_parse_wide_returns_wide_set_per_type():
    for t in ALL_TYPES:
        assert parse_fields_spec("wide", t) == fs._fields_with_preset(t, "wide")


def test_parse_preset_unknown_type_raises():
    with pytest.raises(ValueError, match="No field tags registered"):
        parse_fields_spec("narrow", "unknown")


def test_parse_returned_set_is_fresh_copy():
    """Mutating the returned set must not affect the underlying tag table."""
    result = parse_fields_spec("narrow", "snippet")
    result.add("_scratch")
    assert "_scratch" not in fs._fields_with_preset("snippet", "narrow")


# ── parse_fields_spec: CSV allowlist ─────────────────────────────────


def test_parse_csv_allowlist():
    assert parse_fields_spec("uuid,name", "snippet") == {"uuid", "name"}


def test_parse_csv_strips_whitespace_and_empty():
    assert parse_fields_spec(" uuid , name , ", "snippet") == {"uuid", "name"}


def test_parse_csv_all_commas_falls_through_to_narrow():
    """A CSV with no non-empty tokens is treated as an omitted spec —
    resolves to the narrow default."""
    assert parse_fields_spec(",,,", "snippet") == fs._fields_with_preset(
        "snippet", "narrow"
    )


def test_registered_preset_name_never_falls_through_to_csv(monkeypatch):
    """``"narrow"`` must always resolve as a preset, never as a literal
    field name via the CSV path."""
    monkeypatch.setitem(
        fs._FIELD_TAGS_BY_TYPE,
        "snippet",
        {"uuid": {"narrow"}, "detail": {"narrow"}},
    )
    assert parse_fields_spec("narrow", "snippet") == {"uuid", "detail"}


def test_csv_can_include_flag_field():
    """Explicit CSV allowlists may name a flag field to trigger a
    bundling mechanism."""
    result = parse_fields_spec("uuid,name,_populate", "skill")
    assert result == {"uuid", "name", "_populate"}


# ── should_run_mechanism ─────────────────────────────────────────────


def test_should_run_mechanism_flag_in_allow():
    assert should_run_mechanism({"uuid", "_populate"}, "_populate") is True
    assert should_run_mechanism({"uuid", "_enhance"}, "_enhance") is True


def test_should_run_mechanism_flag_absent():
    assert should_run_mechanism({"uuid", "name"}, "_populate") is False
    assert should_run_mechanism({"uuid", "name"}, "_enhance") is False


def test_full_preset_triggers_every_mechanism():
    """``"full"`` tags every flag field for every type, so
    :func:`should_run_mechanism` fires for each of them."""
    for t in ALL_TYPES:
        allow = parse_fields_spec("full", t)
        tags = fs._FIELD_TAGS_BY_TYPE[t]
        for name in tags:
            if name.startswith("_"):
                assert should_run_mechanism(allow, name) is True, (
                    f"type '{t}' full does not trigger '{name}'"
                )


def test_narrow_skill_does_not_trigger_populate():
    """Skill narrow deliberately excludes ``_populate`` — the list page
    reads counts from ``tool_uuids`` / ``snippet_uuids`` without needing
    the inlined arrays."""
    allow = parse_fields_spec("narrow", "skill")
    assert should_run_mechanism(allow, "_populate") is False


def test_narrow_vmcp_triggers_enhance():
    """vMCP narrow must trigger ``_enhance`` — the Status column reads
    ``running``, which only appears when enhancement runs."""
    allow = parse_fields_spec("narrow", "vmcp")
    assert should_run_mechanism(allow, "_enhance") is True


def test_narrow_vnfs_triggers_enhance():
    allow = parse_fields_spec("narrow", "vnfs")
    assert should_run_mechanism(allow, "_enhance") is True


def test_wide_inherits_narrow_flag_activation():
    """By the preset-ordering invariant, any flag tagged ``"narrow"``
    is also tagged ``"wide"``, so ``wide`` triggers whatever bundling
    ``narrow`` triggers. Concretely: vMCP/vNFS enhancement runs under
    wide; skill population does not (it's only in full for both)."""
    for t in ("vmcp", "vnfs"):
        allow = parse_fields_spec("wide", t)
        assert should_run_mechanism(allow, "_enhance") is True, (
            f"{t}.wide should trigger _enhance (inherited from narrow)"
        )
    assert should_run_mechanism(parse_fields_spec("wide", "skill"), "_populate") is False


# ── select_item_fields ───────────────────────────────────────────────


def test_select_item_fields_returns_fresh_dict_subset():
    item = {"uuid": "u1", "name": "n", "content": "big"}
    result = select_item_fields(item, {"uuid", "name"})
    assert result == {"uuid": "u1", "name": "n"}
    assert result is not item


def test_select_item_fields_full_allowlist_returns_fresh_copy():
    """Even the full allowlist returns a fresh dict — callers can
    freely mutate the result without affecting the source."""
    item = {"uuid": "u1", "name": "n", "content": "big"}
    result = select_item_fields(item, {"uuid", "name", "content"})
    assert result == item
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


def test_select_items_fields_returns_fresh_dicts():
    """Every returned dict is a fresh copy — mutating one must not
    affect the source item."""
    items = [{"uuid": "a"}, {"uuid": "b"}]
    result = select_items_fields(items, {"uuid"})
    assert result == items
    assert result[0] is not items[0]
    assert result[1] is not items[1]


# ── invariants on the preset registry ────────────────────────────────


def test_registered_preset_names():
    """The public preset names are exactly the four called out by the
    spec — minimal / narrow / wide / full — plus nothing else."""
    assert _PRESET_NAMES == {"minimal", "narrow", "wide", "full"}


def test_preset_order():
    """The preset order goes smallest → largest."""
    assert _PRESET_ORDER == ["minimal", "narrow", "wide", "full"]


def test_every_type_has_every_preset():
    """Each registered type must define at least one field tagged with
    every preset name."""
    for t in ALL_TYPES:
        for preset in _PRESET_ORDER:
            assert fs._fields_with_preset(t, preset), (
                f"type '{t}' has no fields tagged '{preset}'"
            )


def test_presets_are_strictly_ordered_per_type():
    """The ordering invariant: for every type,
    ``minimal ⊆ narrow ⊆ wide ⊆ full``. A field tagged with a smaller
    preset must also carry every larger preset tag."""
    for t in ALL_TYPES:
        for smaller, larger in zip(_PRESET_ORDER, _PRESET_ORDER[1:]):
            small_set = fs._fields_with_preset(t, smaller)
            large_set = fs._fields_with_preset(t, larger)
            assert small_set <= large_set, (
                f"type '{t}': '{smaller}' ({sorted(small_set)}) is not a "
                f"subset of '{larger}' ({sorted(large_set)}); "
                f"missing from '{larger}': {sorted(small_set - large_set)}"
            )


def test_full_covers_every_declared_field():
    """Every field in each type's tag table must carry the ``full``
    preset — ``full`` is the total set."""
    for t, tags in _FIELD_TAGS_BY_TYPE.items():
        for name, presets in tags.items():
            assert "full" in presets, (
                f"type '{t}' field '{name}' not tagged 'full' (presets={presets})"
            )


def test_minimal_is_uuid_only_per_type():
    """The ``minimal`` preset is exactly ``{"uuid"}`` on every type —
    it's the search-response identifier preset."""
    for t in ALL_TYPES:
        assert fs._fields_with_preset(t, "minimal") == {"uuid"}


# ── per-type narrow shape (the UI listing-page contract) ─────────────


def test_snippet_narrow_shape():
    assert fs._fields_with_preset("snippet", "narrow") == {
        "uuid",
        "name",
        "description",
        "state",
        "tags",
        "version",
        "content_type",
    }


def test_tool_narrow_shape():
    assert fs._fields_with_preset("tool", "narrow") == {
        "uuid",
        "name",
        "description",
        "state",
        "tags",
        "version",
        "module_name",
    }


def test_skill_narrow_shape():
    assert fs._fields_with_preset("skill", "narrow") == {
        "uuid",
        "name",
        "description",
        "state",
        "tags",
        "version",
        "tool_uuids",
        "snippet_uuids",
    }


def test_vmcp_narrow_shape():
    """vMCP narrow includes ``_enhance``, ``running``, and ``runtime`` —
    enhancement runs and both bundled outputs come with it (the list
    view happens to render only ``running``)."""
    assert fs._fields_with_preset("vmcp", "narrow") == {
        "uuid",
        "name",
        "description",
        "state",
        "tags",
        "version",
        "port",
        "_enhance",
        "running",
        "runtime",
    }


def test_vnfs_narrow_shape():
    assert fs._fields_with_preset("vnfs", "narrow") == {
        "uuid",
        "name",
        "description",
        "state",
        "tags",
        "version",
        "port",
        "protocol",
        "_enhance",
        "running",
        "export_path",
    }


# ── wide invariant: every persisted schema field, no flags ───────────


def test_wide_contains_manifest_base_fields():
    """Every type inherits from ManifestSchema — its base fields must be
    in ``wide`` (and ``full``) for every type."""
    base = {
        "uuid",
        "name",
        "version",
        "description",
        "state",
        "tags",
        "extra",
        "parent",
        "created_at",
        "modified_at",
    }
    for t in ALL_TYPES:
        wide = fs._fields_with_preset(t, "wide")
        assert base <= wide, (
            f"type '{t}' wide is missing manifest fields: {base - wide}"
        )

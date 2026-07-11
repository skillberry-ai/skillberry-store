"""Unit tests for the filter/sort/paginate helpers used by list endpoints."""

from skillberry_store.services.list_query import (
    apply_filters,
    apply_pagination,
    apply_sort,
    is_paginated,
    parse_sort,
)


# ── parse_sort ────────────────────────────────────────────────────────────


def test_parse_sort_default():
    assert parse_sort(None) == ("modified_at", "desc")
    assert parse_sort("") == ("modified_at", "desc")


def test_parse_sort_bare_field_defaults_to_asc():
    assert parse_sort("name") == ("name", "asc")


def test_parse_sort_field_direction():
    assert parse_sort("name:asc") == ("name", "asc")
    assert parse_sort("modified_at:desc") == ("modified_at", "desc")


def test_parse_sort_unknown_direction_falls_back_to_asc():
    assert parse_sort("name:sideways") == ("name", "asc")


def test_parse_sort_whitespace_tolerant():
    assert parse_sort("  name : DESC  ") == ("name", "desc")


# ── apply_filters ────────────────────────────────────────────────────────


ITEMS = [
    {"name": "alpha", "description": "First",  "tags": ["red"],        "state": "approved"},
    {"name": "beta",  "description": "Second", "tags": ["red", "blue"], "state": "new"},
    {"name": "gamma", "description": "Third",  "tags": [],              "state": "approved"},
]


def test_filters_no_params_returns_all():
    assert apply_filters(ITEMS) == ITEMS


def test_filters_search_matches_name():
    result = apply_filters(ITEMS, search="ALP")
    assert [i["name"] for i in result] == ["alpha"]


def test_filters_search_matches_description():
    result = apply_filters(ITEMS, search="second")
    assert [i["name"] for i in result] == ["beta"]


def test_filters_tags_and_semantics():
    result = apply_filters(ITEMS, tags=["red", "blue"])
    assert [i["name"] for i in result] == ["beta"]


def test_filters_tags_missing_tag_matches_nothing():
    assert apply_filters(ITEMS, tags=["nope"]) == []


def test_filters_state_exact_match():
    result = apply_filters(ITEMS, state="approved")
    assert [i["name"] for i in result] == ["alpha", "gamma"]


def test_filters_stacked_as_and():
    result = apply_filters(ITEMS, search="a", tags=["red"], state="approved")
    assert [i["name"] for i in result] == ["alpha"]


# ── apply_sort ──────────────────────────────────────────────────────────


def test_sort_default_modified_at_desc():
    items = [
        {"name": "a", "modified_at": "2024-01-01"},
        {"name": "b", "modified_at": "2024-03-01"},
        {"name": "c", "modified_at": "2024-02-01"},
    ]
    result = apply_sort(items)
    assert [i["name"] for i in result] == ["b", "c", "a"]


def test_sort_name_asc():
    items = [{"name": "b"}, {"name": "a"}, {"name": "c"}]
    result = apply_sort(items, "name:asc")
    assert [i["name"] for i in result] == ["a", "b", "c"]


def test_sort_missing_field_defaults_last_or_first():
    items = [{"name": "b"}, {"name": None}, {"name": "a"}]
    result = apply_sort(items, "name:asc")
    # Missing coerced to '' which sorts first in ascending
    assert [i["name"] for i in result] == [None, "a", "b"]


# ── apply_pagination ────────────────────────────────────────────────────


def test_pagination_no_limit_or_offset_returns_all():
    items = list(range(10))
    # We pass dicts through the real function, so wrap ints.
    dict_items = [{"i": i} for i in items]
    page, total = apply_pagination(dict_items, limit=None, offset=None)
    assert total == 10
    assert page == dict_items


def test_pagination_limit_offset_slice():
    dict_items = [{"i": i} for i in range(10)]
    page, total = apply_pagination(dict_items, limit=3, offset=4)
    assert total == 10
    assert [d["i"] for d in page] == [4, 5, 6]


def test_pagination_offset_past_end_returns_empty_page():
    dict_items = [{"i": i} for i in range(3)]
    page, total = apply_pagination(dict_items, limit=10, offset=100)
    assert total == 3
    assert page == []


def test_pagination_negative_offset_clamped_to_zero():
    dict_items = [{"i": i} for i in range(3)]
    page, total = apply_pagination(dict_items, limit=2, offset=-5)
    assert total == 3
    assert [d["i"] for d in page] == [0, 1]


def test_pagination_negative_limit_yields_empty_page():
    dict_items = [{"i": i} for i in range(3)]
    page, total = apply_pagination(dict_items, limit=-1, offset=0)
    assert total == 3
    assert page == []


# ── is_paginated ────────────────────────────────────────────────────────


def test_is_paginated():
    assert not is_paginated(None, None)
    assert is_paginated(10, None)
    assert is_paginated(None, 0)
    assert is_paginated(0, 0)

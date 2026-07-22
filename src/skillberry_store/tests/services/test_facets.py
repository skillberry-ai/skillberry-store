"""Unit tests for the ``compute_facets`` helper used by /facets/*."""

from skillberry_store.services.facets import compute_facets


def test_empty_input_returns_empty_lists():
    assert compute_facets([]) == {"tags": [], "namespaces": [], "states": []}


def test_dedupes_and_sorts_tags():
    items = [
        {"tags": ["red", "blue"]},
        {"tags": ["red", "green"]},
    ]
    result = compute_facets(items)
    assert result["tags"] == ["blue", "green", "red"]


def test_splits_namespace_prefix_into_separate_list():
    items = [
        {"tags": ["namespace:prod", "red"]},
        {"tags": ["namespace:dev", "red"]},
    ]
    result = compute_facets(items)
    assert result["namespaces"] == ["dev", "prod"]
    assert result["tags"] == ["red"]


def test_ignores_empty_namespace_after_prefix():
    items = [{"tags": ["namespace:", "keep"]}]
    result = compute_facets(items)
    assert result["namespaces"] == []
    assert result["tags"] == ["keep"]


def test_dedupes_and_sorts_states():
    items = [
        {"state": "approved"},
        {"state": "new"},
        {"state": "approved"},
        {"state": None},
        {},
    ]
    result = compute_facets(items)
    assert result["states"] == ["approved", "new"]


def test_tolerates_missing_or_non_iterable_tags():
    items = [
        {},
        {"tags": None},
        {"tags": ["ok"]},
    ]
    result = compute_facets(items)
    assert result["tags"] == ["ok"]


def test_ignores_non_string_tags():
    items = [{"tags": ["ok", None, 42, "", "also"]}]
    result = compute_facets(items)
    assert result["tags"] == ["also", "ok"]

import json

import pytest

from skillberry_store.modules.file_handler import FileHandler
from skillberry_store.modules.lookup_cache import (
    LookupCache,
    build_lookup_cache,
    build_uuid_cache,
    load_json_objects,
)


@pytest.fixture
def root_handler(tmp_path):
    return FileHandler(str(tmp_path))


@pytest.fixture
def skills_handler(tmp_path):
    return FileHandler(str(tmp_path / "skills"))


@pytest.fixture
def tools_handler(tmp_path):
    return FileHandler(str(tmp_path / "tools"))


@pytest.fixture
def snippets_handler(tmp_path):
    return FileHandler(str(tmp_path / "snippets"))


def test_load_json_objects_only_loads_valid_json_dicts(root_handler):
    handler = root_handler
    handler.write_file_content(
        "tool1.json", json.dumps({"uuid": "u1", "name": "tool1"})
    )
    handler.write_file_content("notes.txt", "not json and should be ignored")
    handler.write_file_content("list.json", json.dumps([1, 2, 3]))
    handler.write_file_content("broken.json", "{not-valid-json")

    objects = load_json_objects(handler, "tool")

    assert objects == [{"uuid": "u1", "name": "tool1"}]


def test_build_uuid_cache_skips_objects_without_uuid():
    objects = [
        {"uuid": "s1", "name": "skill-one"},
        {"name": "missing-uuid"},
        {"uuid": "s2", "name": "skill-two"},
    ]

    result = build_uuid_cache(objects, "skill")

    assert result == {
        "s1": {"uuid": "s1", "name": "skill-one"},
        "s2": {"uuid": "s2", "name": "skill-two"},
    }


def test_build_lookup_cache_with_partial_handlers(tools_handler, snippets_handler):
    tools_handler.write_file_content(
        "tool1.json",
        json.dumps({"uuid": "tool-1", "name": "tool-one"}),
    )
    snippets_handler.write_file_content(
        "snippet1.json",
        json.dumps({"uuid": "snippet-1", "name": "snippet-one"}),
    )

    cache = build_lookup_cache(
        tools_handler=tools_handler,
        snippets_handler=snippets_handler,
    )

    assert isinstance(cache, LookupCache)
    assert cache.skills_by_uuid == {}
    assert cache.tools_by_uuid == {"tool-1": {"uuid": "tool-1", "name": "tool-one"}}
    assert cache.snippets_by_uuid == {
        "snippet-1": {"uuid": "snippet-1", "name": "snippet-one"}
    }


def test_build_lookup_cache_indexes_all_requested_stores(
    skills_handler, tools_handler, snippets_handler
):
    skills_handler.write_file_content(
        "skill1.json",
        json.dumps({"uuid": "skill-1", "name": "skill-one", "tool_uuids": ["tool-1"]}),
    )
    tools_handler.write_file_content(
        "tool1.json",
        json.dumps({"uuid": "tool-1", "name": "tool-one"}),
    )
    snippets_handler.write_file_content(
        "snippet1.json",
        json.dumps({"uuid": "snippet-1", "name": "snippet-one"}),
    )

    cache = build_lookup_cache(
        skills_handler=skills_handler,
        tools_handler=tools_handler,
        snippets_handler=snippets_handler,
    )

    assert cache.skills_by_uuid["skill-1"]["name"] == "skill-one"
    assert cache.tools_by_uuid["tool-1"]["name"] == "tool-one"
    assert cache.snippets_by_uuid["snippet-1"]["name"] == "snippet-one"


# Made with Bob

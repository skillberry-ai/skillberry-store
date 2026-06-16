from skillberry_store.fast_api.search_filters import is_simulation_artifact, exclude_simulation


def test_is_simulation_artifact_by_tag():
    assert is_simulation_artifact({"tags": ["simulation"]}) is True
    assert is_simulation_artifact({"tags": ["weather"]}) is False


def test_is_simulation_artifact_by_extra_flag():
    assert is_simulation_artifact({"extra": {"simulation": True}}) is True
    assert is_simulation_artifact({"extra": {}}) is False


def test_exclude_simulation_filters_list():
    items = [
        {"name": "a", "tags": ["weather"]},
        {"name": "b", "tags": ["simulation"]},
        {"name": "c", "extra": {"simulation": True}},
    ]
    assert [i["name"] for i in exclude_simulation(items)] == ["a"]


from unittest.mock import MagicMock


def test_tools_service_list_all_excludes_simulation_by_default():
    from skillberry_store.services.tools_service import ToolsService
    svc = ToolsService.__new__(ToolsService)  # bypass __init__
    svc.handler = MagicMock()
    svc.handler.list_all_dicts.return_value = [
        {"name": "real", "modified_at": "2"},
        {"name": "sim", "tags": ["simulation"], "modified_at": "1"},
    ]
    names = [t["name"] for t in svc.list_all()]
    assert names == ["real"]
    names_incl = sorted(t["name"] for t in svc.list_all(include_simulation=True))
    assert names_incl == ["real", "sim"]

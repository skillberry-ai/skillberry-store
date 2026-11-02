"""The generated proxy module (design D9), as core sees it and as a CLI."""

import ast
import json
import subprocess
import sys

import pytest

from skillberry_plugin_rossoctl_tools import proxy
from skillberry_store.modules.file_executor import (
    detect_tool_dependencies,
    extract_function_and_imports,
    generate_wrapper_any_types,
)
from skillberry_store.tools.anthropic.code_parser import (
    extract_python_functions,
    parse_code_file,
)

SCHEMA = {
    "type": "object",
    "properties": {
        "city": {"type": "string", "description": "City name"},
        "cuisine": {"type": "string"},
        "party_size": {"type": "integer"},
        "open_now": {"type": "boolean"},
        "tags": {"type": "array"},
    },
    "required": ["city"],
}
META = {
    "tool": "reservation-tool",
    "namespace": "team1",
    "port": 8000,
    "path": "/mcp",
    "mcp_tool_name": "search_restaurants",
}


def render(**kw):
    meta = {**META, **kw.pop("meta", {})}
    return proxy.render(
        kw.pop("name", "search_restaurants"),
        meta,
        kw.pop("schema", SCHEMA),
        kw.pop("description", "Search restaurants."),
    )


def test_one_top_level_function_for_core():
    src = render()
    ast.parse(src)
    assert [f["name"] for f in extract_python_functions(src)] == ["search_restaurants"]
    name, params, _imports = extract_function_and_imports(src, "search_restaurants")
    assert name == "search_restaurants"
    assert [(p, k) for p, _t, k in params] == [
        ("city", "positional"),
        ("cuisine", "optional"),
        ("party_size", "optional"),
        ("open_now", "optional"),
        ("tags", "optional"),
    ]
    assert (
        detect_tool_dependencies(
            src, "search_restaurants", {"get_weather", "check_availability"}
        )
        == []
    )
    assert "search_restaurants(city='Boston')" in generate_wrapper_any_types(
        src, "search_restaurants", {"city": "Boston"}, []
    )


def test_reimport_rebuilds_the_same_tool():
    (tool,) = parse_code_file(
        render(), "search_restaurants.py", "scripts/search_restaurants.py", "s"
    )
    d = tool.to_dict()
    assert d["name"] == "search_restaurants"
    assert d["params"]["required"] == ["city"]
    assert {k: v["type"] for k, v in d["params"]["properties"].items()} == {
        "city": "string",
        "cuisine": "string",
        "party_size": "integer",
        "open_now": "boolean",
        "tags": "array",
    }
    assert d["params"]["properties"]["city"]["description"] == "City name"
    assert d["description"].startswith("Search restaurants.")


@pytest.mark.parametrize(
    "text",
    [
        '"""; import os; os.system("x") #',
        "'''",
        "\\x00 nul \x00",
        "a\nb\r\nc",
        "{x} %s",
        "é ünïcode \U0001f600",
    ],
)
def test_hostile_descriptions_are_inert(text):
    src = render(
        description=text,
        schema={
            "type": "object",
            "properties": {"q": {"type": "string", "description": text}},
        },
    )
    ast.parse(src)
    spec = proxy.extract_spec(src)
    assert spec["description"] == text
    assert spec["input_schema"]["properties"]["q"]["description"] == text
    ns = {}
    exec(
        compile(src.replace('if __name__ == "__main__":', "if False:"), "p.py", "exec"),
        ns,
    )
    assert callable(ns["search_restaurants"])


@pytest.mark.parametrize(
    "meta",
    [
        {"tool": "Bad"},
        {"namespace": "a/b"},
        {"mcp_tool_name": "x y"},
        {"port": 0},
        {"port": "80"},
        {"path": "mcp"},
    ],
)
def test_invalid_metadata_is_refused(meta):
    with pytest.raises(ValueError):
        render(meta=meta)


def test_odd_property_names_go_through_kwargs():
    src = render(
        schema={
            "type": "object",
            "properties": {
                "class": {"type": "string"},
                "a-b": {"type": "string"},
                "ok": {"type": "string"},
            },
        }
    )
    _n, params, _i = extract_function_and_imports(src, "search_restaurants")
    assert [p for p, _t, _k in params] == ["ok"]


def test_python_name():
    assert proxy.python_name("get-weather.v2") == "get_weather_v2"
    assert proxy.python_name("2fa") == "t_2fa"
    assert proxy.python_name("class") == "class_"


def _run_cli(src, tmp_path, *args, env=None):
    path = tmp_path / "p.py"
    path.write_text(src)
    return subprocess.run(
        [sys.executable, "-I", str(path), *args],
        capture_output=True,
        text=True,
        timeout=30,
        env={"PATH": "/usr/bin:/bin", **(env or {})},
    )


def test_cli_describe_and_usage(tmp_path):
    r = _run_cli(render(), tmp_path, "--describe")
    assert (
        r.returncode == 0
        and json.loads(r.stdout)["mcp_tool_name"] == "search_restaurants"
    )
    r = _run_cli(render(), tmp_path)
    assert r.returncode == 2 and "--city" in r.stderr


def test_cli_unreachable_is_exit_3(tmp_path):
    r = _run_cli(
        render(),
        tmp_path,
        "--city",
        "Boston",
        env={"ROSSOCTL_NAMESPACE": "nowhere", "ROSSOCTL_TOOL_TIMEOUT": "3"},
    )
    assert r.returncode == 3
    assert "reservation-tool-mcp.nowhere.svc.cluster.local:8000/mcp" in r.stderr


def test_function_raises_when_unreachable(monkeypatch):
    monkeypatch.setenv("ROSSOCTL_BACKEND_URL", "http://127.0.0.1:9")
    ns = {}
    exec(render(), ns)
    with pytest.raises(RuntimeError, match="unreachable"):
        ns["search_restaurants"](city="Boston")

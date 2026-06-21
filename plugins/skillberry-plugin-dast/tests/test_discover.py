"""Tests for entry-point discovery (Tier-1 tools + Tier-2 AST)."""

from skillberry_plugin_dast.engine.discover import discover_entry_points


def test_tier1_from_tools():
    tools = [
        {
            "name": "send_msg",
            "uuid": "t1",
            "module_name": "send.py",
            "params": {
                "properties": {"channel": {"type": "string"}},
                "required": ["channel"],
                "optional": [],
            },
        }
    ]
    eps = discover_entry_points(tools, [])
    assert len(eps) == 1
    ep = eps[0]
    assert ep.name == "send_msg"
    assert ep.kind == "tool"
    assert ep.tool_uuid == "t1"
    assert ep.params["required"] == ["channel"]


def test_tier2_public_functions_classes_and_main():
    source = (
        "import os\n"
        "def public_fn(a, b=2):\n    return a + b\n"
        "def _private():\n    pass\n"
        "class PublicCls:\n    def __init__(self, x):\n        self.x = x\n"
        "class _Hidden:\n    pass\n"
        "if __name__ == '__main__':\n    public_fn(1)\n"
    )
    eps = discover_entry_points([], [("mod.py", source)])
    names = {(e.name, e.kind) for e in eps}
    assert ("public_fn", "function") in names
    assert ("PublicCls", "class") in names
    assert ("__main__", "main") in names
    # private excluded
    assert not any(e.name in ("_private", "_Hidden") for e in eps)
    # signature captured (self stripped)
    fn = next(e for e in eps if e.name == "public_fn")
    assert fn.signature == ["a", "b"]
    cls = next(e for e in eps if e.name == "PublicCls")
    assert cls.signature == ["x"]


def test_tier2_dedup_against_tier1():
    # A module defines `send_msg`, which is also a registered tool -> Tier-1 wins.
    tools = [{"name": "send_msg", "uuid": "t1", "module_name": "send.py", "params": {}}]
    source = "def send_msg(x):\n    pass\ndef helper(y):\n    pass\n"
    eps = discover_entry_points(tools, [("send.py", source)])
    send = [e for e in eps if e.name == "send_msg"]
    assert len(send) == 1 and send[0].kind == "tool"  # not duplicated as function
    assert any(e.name == "helper" and e.kind == "function" for e in eps)


def test_bad_syntax_module_yields_no_tier2():
    eps = discover_entry_points([], [("broken.py", "def (:\n  nope")])
    assert eps == []


def test_nested_defs_not_discovered():
    source = "def outer():\n    def inner():\n        pass\n    return inner\n"
    eps = discover_entry_points([], [("m.py", source)])
    assert [e.name for e in eps] == ["outer"]  # inner is nested, not top-level

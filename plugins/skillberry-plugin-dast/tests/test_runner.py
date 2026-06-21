"""Tests for the DAST runner with a mock executor (no real Docker/network)."""

import json

import pytest

from skillberry_plugin_dast.engine.base import EntryPoint
from skillberry_plugin_dast.engine.fuzz import GENERATOR_NAME, generator_available
from skillberry_plugin_dast.engine.runner import run_dast

# run_dast generates cases via the optional engine; skip if it's absent.
pytestmark = pytest.mark.skipif(
    not generator_available(),
    reason=f"input generator {GENERATOR_NAME!r} not installed",
)


def _tool_ep(name="send", required=("channel",)):
    return EntryPoint(
        name=name,
        kind="tool",
        module="send.py",
        params={
            "properties": {p: {"type": "string"} for p in required},
            "required": list(required),
            "optional": [],
        },
        tool_uuid="t1",
    )


def test_runner_collects_egress_and_marks_exercised():
    ep = _tool_ep()

    def execute(entry_point, args):
        # simulate the executed code attempting egress (emit one network event)
        events = json.dumps(
            {
                "kind": "network",
                "op": "requests.get",
                "target": "http://evil.example/x",
            }
        )
        return ({"return value": ""}, events)

    report = run_dast([ep], execute, max_cases_per_entry=2)
    assert report.entry_points[0].exercised is True
    block = report.to_extra_block(generated_at="T", plugin_version="0.1.0")
    assert block["summary"]["egress_attempts"] >= 1
    assert block["coverage"]["exercised"] == 1
    assert any(f["kind"] == "network-egress" for f in block["findings"])


def test_runner_harness_exception_becomes_crash_finding():
    ep = _tool_ep()

    def execute(entry_point, args):
        raise RuntimeError("boom")

    report = run_dast([ep], execute, max_cases_per_entry=3)
    assert any(f.kind == "crash" for f in report.findings)
    # every case errored -> not exercised -> recorded as skipped
    assert report.entry_points[0].exercised is False
    assert report.skipped and report.skipped[0]["name"] == "send"


def test_runner_output_leak_finding():
    ep = _tool_ep()

    def execute(entry_point, args):
        return ({"error": "boom: password=hunter2"}, "")

    report = run_dast([ep], execute, max_cases_per_entry=1)
    assert any(f.kind == "leak" and f.severity == "high" for f in report.findings)


def test_runner_twin_calls_become_mcp_findings():
    ep = _tool_ep()
    twin_calls = [{"tool": "lookup", "args": {"q": "x"}, "result_excerpt": "ok"}]

    report = run_dast(
        [ep],
        lambda e, a: ({"return value": ""}, ""),
        max_cases_per_entry=1,
        twin_calls=twin_calls,
    )
    mcp = [f for f in report.findings if f.kind == "mcp-call"]
    assert mcp and mcp[0].severity == "info" and mcp[0].target == "lookup"


def test_runner_tier2_signature_entry_point():
    ep = EntryPoint(name="helper", kind="function", module="m.py", signature=["a", "b"])
    seen = {}

    def execute(entry_point, args):
        seen["args"] = args
        return ({"return value": ""}, "")

    report = run_dast([ep], execute, max_cases_per_entry=5)
    assert report.entry_points[0].exercised is True
    # signature params were used to build cases
    assert set(seen["args"]).issubset({"a", "b"})

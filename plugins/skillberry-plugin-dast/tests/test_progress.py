"""Tests for the scan-progress registry and the runner progress callback."""

import pytest

from skillberry_plugin_dast.engine import progress
from skillberry_plugin_dast.engine.base import EntryPoint
from skillberry_plugin_dast.engine.fuzz import GENERATOR_NAME, generator_available
from skillberry_plugin_dast.engine.runner import run_dast

# The registry tests are engine-free; the run_dast tests need the generator.
_needs_engine = pytest.mark.skipif(
    not generator_available(),
    reason=f"input generator {GENERATOR_NAME!r} not installed",
)


def test_registry_lifecycle():
    progress.clear("u1")
    assert progress.get("u1") is None

    progress.start("u1", total=3)
    p = progress.get("u1")
    assert p["state"] == "running" and p["total"] == 3 and p["current"] == 0

    progress.update("u1", current=2, entry_point="send_msg")
    p = progress.get("u1")
    assert p["current"] == 2 and p["entry_point"] == "send_msg"

    progress.finish("u1")
    p = progress.get("u1")
    assert p["state"] == "done" and p["entry_point"] is None
    progress.clear("u1")
    assert progress.get("u1") is None


def test_runner_invokes_progress_callback_per_entry_point():
    eps = [
        EntryPoint(name="a", kind="function", module="m.py", signature=[]),
        EntryPoint(name="b", kind="function", module="m.py", signature=[]),
    ]
    seen = []

    def cb(current, total, name):
        seen.append((current, total, name))

    run_dast(
        eps,
        lambda e, args: ({"return value": ""}, ""),
        max_cases_per_entry=1,
        progress_callback=cb,
    )
    assert seen == [(1, 2, "a"), (2, 2, "b")]


def test_runner_swallows_callback_errors():
    eps = [EntryPoint(name="a", kind="function", module="m.py", signature=[])]

    def boom(current, total, name):
        raise RuntimeError("nope")

    # must not raise despite the callback throwing
    report = run_dast(
        eps,
        lambda e, args: ({"return value": ""}, ""),
        max_cases_per_entry=1,
        progress_callback=boom,
    )
    assert report.entry_points[0].exercised is True

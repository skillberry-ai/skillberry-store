"""Tests for the observe shim/event parser and output-based findings."""

import json

from skillberry_plugin_dast.engine.observe import (
    EVENT_MARKER,
    SHIM_SOURCE,
    findings_from_output,
    parse_events,
    split_events_from_output,
)


def test_split_events_from_output():
    ev = json.dumps({"kind": "network", "op": "socket.connect", "target": "evil:80"})
    stdout = "real line 1\n" + EVENT_MARKER + ev + "\n" + "real line 2\n"
    events, clean = split_events_from_output(stdout)
    assert events == ev  # marker stripped, JSON recovered
    assert clean == "real line 1\nreal line 2"
    # the recovered events feed straight into parse_events
    findings = parse_events(events, entry_point="ep", case="c")
    assert findings and findings[0].kind == "network-egress"


def _sink(*events):
    return "\n".join(json.dumps(e) for e in events)


def test_parse_network_egress_is_high_and_excludes_loopback():
    text = _sink(
        {"kind": "network", "op": "requests.get", "target": "http://evil.example/x"},
        {"kind": "network", "op": "socket.connect", "target": "127.0.0.1:10000"},
        {"kind": "network", "op": "socket.connect", "target": "host.docker.internal:1"},
    )
    findings = parse_events(text, entry_point="ep", case="c")
    # only the non-loopback egress is a finding
    assert len(findings) == 1
    f = findings[0]
    assert f.kind == "network-egress" and f.severity == "high"
    assert "evil.example" in f.target


def test_parse_subprocess_high_and_fs_write_medium_read_low():
    text = _sink(
        {"kind": "subprocess", "op": "Popen", "target": "['curl']"},
        {"kind": "filesystem", "op": "open.write", "target": "/etc/x"},
        {"kind": "filesystem", "op": "open.read", "target": "/data"},
    )
    findings = parse_events(text, entry_point="ep", case="c")
    by_kind = {f.kind: f for f in findings}
    assert by_kind["subprocess"].severity == "high"
    assert by_kind["filesystem"].severity in ("medium", "low")
    sev = {f.severity for f in findings if f.kind == "filesystem"}
    assert "medium" in sev and "low" in sev


def test_parse_ignores_blank_and_bad_lines():
    text = "not json\n\n" + json.dumps(
        {"kind": "subprocess", "op": "os.system", "target": "rm"}
    )
    findings = parse_events(text, entry_point="ep", case="c")
    assert len(findings) == 1


def test_findings_from_output_crash_and_leak():
    result = {
        "error": 'Traceback (most recent call last):\n  File "x", line 1',
        "stderr": "API_KEY=sk-secret-123",
    }
    findings = findings_from_output(result, entry_point="ep", case="c")
    kinds = {f.kind for f in findings}
    assert "crash" in kinds
    assert "leak" in kinds
    leak = next(f for f in findings if f.kind == "leak")
    assert leak.severity == "high"


def test_findings_from_clean_output_none():
    result = {"return value": "ok, all good"}
    assert findings_from_output(result, entry_point="ep", case="c") == []


def test_shim_does_not_observe_its_own_sink(tmp_path):
    # Exec the shim in a fresh namespace and confirm the event sink writes are
    # NOT recorded as filesystem findings (the recursion/flood regression).
    # The shim patches global builtins.open/socket/etc., so restore them after.
    import builtins
    import os
    import socket
    import subprocess

    saved = (builtins.open, socket.socket.connect, subprocess.Popen.__init__)
    sink = str(tmp_path / "events.jsonl")
    builtins.open(sink, "w").close()
    prev = os.environ.get("DAST_EVENT_SINK")
    os.environ["DAST_EVENT_SINK"] = sink
    try:
        exec(compile(SHIM_SOURCE, "<shim>", "exec"), {})
        # trigger a real write to a DIFFERENT file via the (now-wrapped) open
        target = str(tmp_path / "out.txt")
        builtins.open(target, "w").write("x")
        text = saved[0](sink).read()  # read sink via the original open
    finally:
        builtins.open = saved[0]
        socket.socket.connect = saved[1]
        subprocess.Popen.__init__ = saved[2]
        if prev is None:
            os.environ.pop("DAST_EVENT_SINK", None)
        else:
            os.environ["DAST_EVENT_SINK"] = prev
    findings = parse_events(text, entry_point="ep", case="c")
    fs = [f for f in findings if f.kind == "filesystem"]
    # the out.txt write is recorded; the sink's own writes are not
    assert any("out.txt" in (f.target or "") for f in fs)
    assert not any("events.jsonl" in (f.target or "") for f in findings)


def test_shim_source_is_pass_through_not_block():
    # The shim must call the originals (pass-through) and never raise/sys.exit.
    assert "_orig_connect(self, address" in SHIM_SOURCE
    assert "_orig_req(self, method, url" in SHIM_SOURCE
    assert "sys.exit" not in SHIM_SOURCE
    assert "raise" not in SHIM_SOURCE
    # it must compile
    compile(SHIM_SOURCE, "<shim>", "exec")

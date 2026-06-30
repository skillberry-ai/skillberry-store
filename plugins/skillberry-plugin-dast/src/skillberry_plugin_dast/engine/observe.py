"""Effect observation — detect-and-report shim + finding parser.

Two halves:

  - ``SHIM_SOURCE`` is self-contained Python source **prepended to the tool's
    code** before execution, so it runs inside the *target's* interpreter (local
    or the store's Docker exec sandbox) with no env/mount cooperation needed. It
    monkeypatches the network / subprocess / filesystem entry points to **log and
    pass through** — it never blocks. Each intercepted call is emitted to stdout
    as an ``EVENT_MARKER``-prefixed JSON line (the only channel that survives the
    Docker path, which returns just stdout); a ``DAST_EVENT_SINK`` file is also
    written when set. Detect-and-report only.

  - ``split_events_from_output`` separates the markered event lines from the
    tool's real stdout; ``parse_events`` / ``findings_from_output`` turn the
    events and a tool's ``{return value|error}`` into ``Finding`` objects.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from .base import (
    FINDING_CRASH,
    FINDING_FILESYSTEM,
    FINDING_LEAK,
    FINDING_NETWORK,
    FINDING_SUBPROCESS,
    SEV_HIGH,
    SEV_LOW,
    SEV_MEDIUM,
    Finding,
)

# Env var the shim writes its JSONL event stream to (optional fallback).
EVENT_SINK_ENV = "DAST_EVENT_SINK"

# Marker prefixing each event the shim prints to stdout. stdout is the only
# channel that survives BOTH local exec() and the store's Docker exec path
# (which returns only stdout), so it is the primary event transport. The runner
# strips these lines out of the tool's real output before parsing the result.
EVENT_MARKER = "__DAST_EVENT__:"

# ── the shim (runs inside the target interpreter) ────────────────────────────
# Pass-through-and-log wrappers around socket/urllib/requests/httpx/subprocess/
# os.system/open. Best-effort: any wrap failure is swallowed so the target runs
# normally. NOTE: detect-and-report — nothing here blocks an operation.
#
# It is injected by PREPENDING this source to the tool's code, so it travels
# inside the executed program and needs no env/mount cooperation from the
# executor. Events go to stdout (marker-prefixed) and, if set, a sink file.
SHIM_SOURCE = 'EVENT_MARKER = "' + EVENT_MARKER + '"\n' + r"""
import os as _os, sys as _sys, json as _json, time as _time, builtins as _bi

_SINK = _os.environ.get("DAST_EVENT_SINK")
# Capture ORIGINAL open + stdout.write BEFORE wrapping so the emitter's own
# activity is not re-observed (which would flood/recurse).
_ORIG_OPEN = _bi.open
_ORIG_STDOUT_WRITE = _sys.stdout.write

def _emit(kind, op, target):
    rec = _json.dumps({"kind": kind, "op": op, "target": str(target)[:500],
                       "ts": _time.time()})
    try:
        _ORIG_STDOUT_WRITE(EVENT_MARKER + rec + "\n")
        _sys.stdout.flush()
    except Exception:
        pass
    if _SINK:
        try:
            with _ORIG_OPEN(_SINK, "a", encoding="utf-8") as fh:
                fh.write(rec + "\n")
        except Exception:
            pass

# ── network: socket.connect ──────────────────────────────────────────────────
try:
    import socket as _socket
    _orig_connect = _socket.socket.connect
    def _connect(self, address, *a, **k):
        _emit("network", "socket.connect", address)
        return _orig_connect(self, address, *a, **k)
    _socket.socket.connect = _connect
except Exception:
    pass

# ── network: urllib ──────────────────────────────────────────────────────────
try:
    import urllib.request as _ur
    _orig_urlopen = _ur.urlopen
    def _urlopen(url, *a, **k):
        target = getattr(url, "full_url", url)
        _emit("network", "urllib.urlopen", target)
        return _orig_urlopen(url, *a, **k)
    _ur.urlopen = _urlopen
except Exception:
    pass

# ── network: requests ────────────────────────────────────────────────────────
try:
    import requests as _rq
    _orig_req = _rq.sessions.Session.request
    def _request(self, method, url, *a, **k):
        _emit("network", "requests." + str(method).lower(), url)
        return _orig_req(self, method, url, *a, **k)
    _rq.sessions.Session.request = _request
except Exception:
    pass

# ── network: httpx ───────────────────────────────────────────────────────────
try:
    import httpx as _hx
    _orig_hx = _hx.Client.request
    def _hx_request(self, method, url, *a, **k):
        _emit("network", "httpx." + str(method).lower(), url)
        return _orig_hx(self, method, url, *a, **k)
    _hx.Client.request = _hx_request
except Exception:
    pass

# ── subprocess + os.system ───────────────────────────────────────────────────
try:
    import subprocess as _sp
    _orig_popen = _sp.Popen.__init__
    def _popen_init(self, args, *a, **k):
        _emit("subprocess", "Popen", args)
        return _orig_popen(self, args, *a, **k)
    _sp.Popen.__init__ = _popen_init
except Exception:
    pass
try:
    _orig_system = _os.system
    def _system(cmd):
        _emit("subprocess", "os.system", cmd)
        return _orig_system(cmd)
    _os.system = _system
except Exception:
    pass

# ── filesystem: open (writes are higher-signal than reads) ───────────────────
try:
    def _open(file, mode="r", *a, **k):
        # Never observe our own event-sink writes (would recurse/flood).
        if _SINK and str(file) == _SINK:
            return _ORIG_OPEN(file, mode, *a, **k)
        op = "open.write" if any(c in str(mode) for c in ("w", "a", "x", "+")) else "open.read"
        _emit("filesystem", op, file)
        return _ORIG_OPEN(file, mode, *a, **k)
    _bi.open = _open
except Exception:
    pass
"""

# ── finding extraction ───────────────────────────────────────────────────────

# Hosts/paths that are part of the harness itself — not findings.
_BENIGN_TARGETS = ("127.0.0.1", "localhost", "host.docker.internal", "172.17.0.1")

# Cheap secret/leak signatures in tool output.
_SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|secret|password|token|authorization|bearer|aws_secret)"
    r"\s*[=:]\s*\S+"
)
_TRACEBACK_RE = re.compile(r"Traceback \(most recent call last\)|File \".*\", line \d+")


def _event_kind_to_finding(kind: str) -> str:
    return {
        "network": FINDING_NETWORK,
        "subprocess": FINDING_SUBPROCESS,
        "filesystem": FINDING_FILESYSTEM,
    }.get(kind, FINDING_NETWORK)


def _is_benign_network(target: str) -> bool:
    return any(b in (target or "") for b in _BENIGN_TARGETS)


def split_events_from_output(stdout: str) -> tuple:
    """Separate marker-prefixed shim events from the tool's real stdout.

    Returns ``(events_jsonl, clean_output)``: ``events_jsonl`` is the newline-
    joined JSON records the shim emitted (each line was ``EVENT_MARKER`` + JSON),
    and ``clean_output`` is the remaining output with those lines removed.
    """
    event_lines: List[str] = []
    clean_lines: List[str] = []
    for line in (stdout or "").splitlines():
        if line.startswith(EVENT_MARKER):
            event_lines.append(line[len(EVENT_MARKER) :])
        else:
            clean_lines.append(line)
    return "\n".join(event_lines), "\n".join(clean_lines)


def parse_events(sink_text: str, *, entry_point: str, case: str) -> List[Finding]:
    """Turn the shim's JSONL event stream into Findings.

    Network egress to a non-harness host is high severity (potential exfil);
    subprocess spawning is high; filesystem writes are medium, reads low.
    """
    findings: List[Finding] = []
    for line in (sink_text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        kind = ev.get("kind")
        op = ev.get("op", "")
        target = ev.get("target", "")

        if kind == "network":
            if _is_benign_network(target):
                continue  # the vMCP twin / loopback — expected, not a finding
            sev = SEV_HIGH
        elif kind == "subprocess":
            sev = SEV_HIGH
        elif kind == "filesystem":
            sev = SEV_MEDIUM if "write" in op else SEV_LOW
        else:
            sev = SEV_LOW

        findings.append(
            Finding(
                entry_point=entry_point,
                kind=_event_kind_to_finding(kind),
                severity=sev,
                case=case,
                evidence=op,
                target=target,
            )
        )
    return findings


def findings_from_output(
    result: Dict[str, Any], *, entry_point: str, case: str
) -> List[Finding]:
    """Findings derived from a tool's execution result (crash / leak)."""
    findings: List[Finding] = []
    text = ""
    if isinstance(result, dict):
        text = str(result.get("error") or "") + "\n" + str(result.get("stderr") or "")
        if "return value" in result:
            text += "\n" + str(result.get("return value") or "")

    if isinstance(result, dict) and result.get("error"):
        err = str(result.get("error") or "")
        # A timeout/hang is a reliability/DoS finding in its own right.
        if "timed out" in err.lower():
            findings.append(
                Finding(
                    entry_point=entry_point,
                    kind=FINDING_CRASH,
                    severity=SEV_MEDIUM,
                    case=case,
                    evidence=err[:200],
                )
            )
        elif _TRACEBACK_RE.search(text):
            findings.append(
                Finding(
                    entry_point=entry_point,
                    kind=FINDING_CRASH,
                    severity=SEV_MEDIUM,
                    case=case,
                    evidence=_first_match(_TRACEBACK_RE, text),
                )
            )

    if _SECRET_RE.search(text):
        findings.append(
            Finding(
                entry_point=entry_point,
                kind=FINDING_LEAK,
                severity=SEV_HIGH,
                case=case,
                evidence=_first_match(_SECRET_RE, text),
            )
        )
    return findings


def _first_match(rx: re.Pattern, text: str) -> str:
    m = rx.search(text or "")
    return (m.group(0) if m else "")[:200]

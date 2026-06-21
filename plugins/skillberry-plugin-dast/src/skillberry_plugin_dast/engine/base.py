"""Shapes + vocabulary for the DAST engine.

The engine discovers a skill's invocable entry points, exercises each with
adversarial inputs, observes the effects, and assembles a ``DastReport`` that
serializes to the ``extra["dast"]`` block the plugin persists. Everything here is
pure and JSON-friendly so the engine can be unit-tested offline; ``generated_at``
is injected by the plugin (not computed here) to keep output deterministic.

Honest framing baked into the vocabulary:
  - discovery is STATIC (Tier-3 dynamic dispatch may be missed) -> reported in
    ``coverage.discovery``;
  - observation is DETECT-AND-REPORT (effects happen, are not prevented) ->
    reported in ``coverage.observation``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = 1
MODE = "detect-and-report"

OBJECT_TYPES = ("skill", "tool", "snippet")

# Entry-point tiers / kinds.
KIND_TOOL = "tool"  # Tier 1: a registered store tool
KIND_FUNCTION = "function"  # Tier 2: AST-discovered public function
KIND_CLASS = "class"  # Tier 2: AST-discovered public class
KIND_MAIN = "main"  # Tier 2: a module __main__ entry point

# Finding kinds (effect classes the observer / twin surface).
FINDING_CRASH = "crash"
FINDING_LEAK = "leak"
FINDING_NETWORK = "network-egress"
FINDING_SUBPROCESS = "subprocess"
FINDING_FILESYSTEM = "filesystem"
FINDING_MCP = "mcp-call"

# Severities.
SEV_HIGH = "high"
SEV_MEDIUM = "medium"
SEV_LOW = "low"
SEV_INFO = "info"
_SEV_ORDER = {SEV_INFO: 0, SEV_LOW: 1, SEV_MEDIUM: 2, SEV_HIGH: 3}


@dataclass
class EntryPoint:
    """One externally-invocable surface of a skill."""

    name: str
    kind: str  # KIND_*
    module: str = ""  # module file the entry point lives in
    # Tier-1 tools carry a param schema; Tier-2 callables carry a signature.
    params: Optional[Dict[str, Any]] = None  # {properties, required, optional}
    signature: List[str] = field(default_factory=list)  # param names (Tier-2)
    tool_uuid: Optional[str] = None
    exercised: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "module": self.module,
            "params_or_signature": (
                self.params if self.params is not None else self.signature
            ),
            "exercised": self.exercised,
        }


@dataclass
class Finding:
    """One thing observed while exercising an entry point."""

    entry_point: str
    kind: str  # FINDING_*
    severity: str  # SEV_*
    case: str = ""  # short label of the adversarial input that triggered it
    evidence: str = ""  # excerpt (traceback line, leaked token, etc.)
    target: Optional[str] = None  # host/path/command, when applicable

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_point": self.entry_point,
            "kind": self.kind,
            "severity": self.severity,
            "case": self.case,
            "evidence": self.evidence,
            "target": self.target,
        }


@dataclass
class DastReport:
    """Full result for one scanned object."""

    entry_points: List[EntryPoint] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    # entry points discovered but not run (e.g. unreadable module), for honesty.
    skipped: List[Dict[str, str]] = field(default_factory=list)
    # Calls actually executed (exercised), by surface. A "call" is one
    # input-case run against an entry point. These count ALL executions, not
    # just the ones that surfaced a problem.
    direct_calls_exercised: int = 0
    mcp_calls_exercised: int = 0

    # ── helpers ──────────────────────────────────────────────────────────────

    def _by_tier(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for ep in self.entry_points:
            out[ep.kind] = out.get(ep.kind, 0) + 1
        return out

    def _exercised_count(self) -> int:
        return sum(1 for ep in self.entry_points if ep.exercised)

    def _sev_count(self, severity: str) -> int:
        return sum(1 for f in self.findings if f.severity == severity)

    def _kind_count(self, kind: str) -> int:
        return sum(1 for f in self.findings if f.kind == kind)

    def _mcp_tools_count(self) -> int:
        """Distinct tools exercised via the MCP twin (mcp-call findings)."""
        return len({f.entry_point for f in self.findings if f.kind == FINDING_MCP})

    # ``mcp-call`` is an observation (info), not a problem. Every other finding
    # kind is an actual problem (crash/leak/egress/subprocess/filesystem).
    def _problems(self) -> List[Finding]:
        return [f for f in self.findings if f.kind != FINDING_MCP]

    def _problem_count(self) -> int:
        return len(self._problems())

    # ── serialization ──────────────────────────────────────────────────────────

    def to_extra_block(
        self, *, generated_at: str, plugin_version: str
    ) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": generated_at,
            "scanner": {"plugin_version": plugin_version, "mode": MODE},
            "coverage": {
                "entry_points_discovered": len(self.entry_points),
                "exercised": self._exercised_count(),
                "skipped": len(self.skipped),
                "by_tier": self._by_tier(),
                # MCP surface (driven via the benign twin) is separate from the
                # direct-invocation entry points above, so it gets its own count
                # — otherwise an mcp-scope scan misleadingly reads "0/0".
                "mcp_tools_exercised": self._mcp_tools_count(),
                "discovery": "static (Tier-3 dynamic dispatch may be missed)",
                "observation": "detected, not prevented",
            },
            "entry_points": [
                ep.to_dict() for ep in sorted(self.entry_points, key=lambda e: e.name)
            ],
            "findings": [
                f.to_dict()
                for f in sorted(
                    self.findings,
                    key=lambda f: (
                        -_SEV_ORDER.get(f.severity, 0),
                        f.entry_point,
                        f.kind,
                    ),
                )
            ],
            "skipped_entry_points": sorted(
                self.skipped, key=lambda s: s.get("name", "")
            ),
            "summary": {
                # Calls actually executed (exercised), by surface.
                "exercised": {
                    "direct_calls": self.direct_calls_exercised,
                    "mcp_calls": self.mcp_calls_exercised,
                    "total": self.direct_calls_exercised + self.mcp_calls_exercised,
                },
                # Actual findings (real issues, NOT mere observations), by surface.
                "findings": {
                    "direct": sum(
                        1 for f in self._problems() if f.severity != SEV_INFO
                    ),
                    "mcp": 0,  # MCP-path observations are info, not findings
                    "total": self._problem_count(),
                    "high": self._sev_count(SEV_HIGH),
                    "medium": self._sev_count(SEV_MEDIUM),
                },
                # Effect breakdown among findings.
                "egress_attempts": self._kind_count(FINDING_NETWORK),
                "subprocess_attempts": self._kind_count(FINDING_SUBPROCESS),
                "crashes": self._kind_count(FINDING_CRASH),
            },
        }

    def summary_tags(self) -> List[str]:
        tags = [
            f"dast:findings:{len(self.findings)}",
            f"dast:coverage:{self._exercised_count()}/{len(self.entry_points)}",
        ]
        high = self._sev_count(SEV_HIGH)
        if high:
            tags.append(f"dast:high:{high}")
        egress = self._kind_count(FINDING_NETWORK)
        if egress:
            tags.append(f"dast:egress:{egress}")
        return tags

"""DAST runner — exercise each entry point with adversarial cases, collect findings.

The runner is the orchestration core: discover → fuzz → execute → observe. It is
decoupled from the store and Docker through an injected ``execute`` callable, so
it is fully unit-testable with a mock executor (no real sandbox/network in CI).

``execute(entry_point, args) -> (result, events_text)``:
  - ``result`` is the tool's ``{return value|error|stderr}`` dict,
  - ``events_text`` is the JSONL the observe-shim wrote for that run (or "").

The plugin supplies a real ``execute`` that drives ``FileExecutor`` with the
observe-shim installed and the event sink read back; tests supply a fake.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import KIND_TOOL, DastReport, EntryPoint, Finding
from .fuzz import cases_from_signature, generate_cases
from .observe import findings_from_output, parse_events

logger = logging.getLogger(__name__)

# execute(entry_point, args_dict) -> (result_dict, events_jsonl_text)
ExecuteFn = Callable[[EntryPoint, Dict[str, Any]], Tuple[Dict[str, Any], str]]
# progress_callback(current_index, total, entry_point_name)
ProgressFn = Callable[[int, int, str], None]


def _cases_for(ep: EntryPoint, max_cases: int) -> List[Dict[str, Any]]:
    if ep.params is not None:
        return generate_cases(ep.params, max_cases=max_cases)
    return cases_from_signature(ep.signature, max_cases=max_cases)


def run_dast(
    entry_points: List[EntryPoint],
    execute: ExecuteFn,
    *,
    max_cases_per_entry: int = 24,
    twin_calls: List[Dict[str, Any]] | None = None,
    progress_callback: Optional[ProgressFn] = None,
) -> DastReport:
    """Exercise every entry point and assemble a DastReport.

    ``twin_calls`` (optional) is the benign vMCP twin's observed-call log; each
    becomes an informational ``mcp-call`` finding so the report shows what tool
    traffic the skill generated.

    ``progress_callback`` (optional) is invoked before each entry point with
    ``(current_index, total, entry_point_name)`` so a caller can publish live
    progress for the UI. Best-effort: callback exceptions are swallowed.
    """
    report = DastReport(entry_points=list(entry_points))
    total = len(report.entry_points)

    for idx, ep in enumerate(report.entry_points, start=1):
        if progress_callback is not None:
            try:
                progress_callback(idx, total, ep.name)
            except Exception:
                pass
        cases = _cases_for(ep, max_cases_per_entry)
        exercised_any = False
        for case in cases:
            try:
                result, events_text = execute(ep, case["args"])
            except Exception as e:
                # An exception escaping the harness itself is a crash finding.
                report.findings.append(
                    Finding(
                        entry_point=ep.name,
                        kind="crash",
                        severity="medium",
                        case=case["label"],
                        evidence=f"harness exception: {e}"[:200],
                    )
                )
                continue
            exercised_any = True
            report.direct_calls_exercised += 1
            report.findings.extend(
                parse_events(events_text, entry_point=ep.name, case=case["label"])
            )
            report.findings.extend(
                findings_from_output(result, entry_point=ep.name, case=case["label"])
            )
        ep.exercised = exercised_any
        if not exercised_any:
            report.skipped.append(
                {"name": ep.name, "reason": "no case could be executed"}
            )

    # Fold in MCP twin observations (informational — exercised calls, not
    # problems). Each recorded twin call is one MCP call exercised.
    for call in twin_calls or []:
        report.mcp_calls_exercised += 1
        report.findings.append(
            Finding(
                entry_point=str(call.get("tool", "")),
                kind="mcp-call",
                severity="info",
                case="twin",
                evidence=str(call.get("args", ""))[:200],
                target=str(call.get("tool", "")),
            )
        )

    return report

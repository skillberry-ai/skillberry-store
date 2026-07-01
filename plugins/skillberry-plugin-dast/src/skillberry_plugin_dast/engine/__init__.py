"""DAST engine: discover -> fuzz -> execute -> observe -> report.

Each stage is an independently testable module. The plugin wires them to the
store (FileExecutor + benign vMCP twin); the engine itself is store-decoupled.
"""

from __future__ import annotations

from .base import (
    DastReport,
    EntryPoint,
    Finding,
)
from . import progress, scope
from .discover import discover_entry_points
from .fuzz import (
    GENERATOR_NAME,
    cases_from_signature,
    generate_cases,
    generator_available,
    generator_status,
)
from .observe import EVENT_SINK_ENV, SHIM_SOURCE, findings_from_output, parse_events
from .runner import run_dast
from .twin import BenignMcpTwin, host_address_for_container

__all__ = [
    "DastReport",
    "EntryPoint",
    "Finding",
    "discover_entry_points",
    "generate_cases",
    "cases_from_signature",
    "generator_available",
    "generator_status",
    "GENERATOR_NAME",
    "SHIM_SOURCE",
    "EVENT_SINK_ENV",
    "parse_events",
    "findings_from_output",
    "run_dast",
    "BenignMcpTwin",
    "host_address_for_container",
    "progress",
    "scope",
]

"""Base classes for SAST engines.

A SAST engine wraps an open-source static-analysis tool (e.g. Bandit) behind a
uniform interface so the plugin can run one or several of them and merge their
findings into a single normalized shape. Add a new engine by subclassing
``SastEngine`` and registering it in ``engines/__init__.py``.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional

# Normalized severity ladder, low -> critical. Engine-specific severities are
# mapped onto these so findings from different tools are comparable.
SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"
SEVERITY_CRITICAL = "critical"

SEVERITIES = (SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH, SEVERITY_CRITICAL)


@dataclass
class Finding:
    """A single normalized static-analysis finding.

    Fields are common across engines; ``rule_id`` and ``message`` are the
    engine's own identifiers/text, while ``severity`` is normalized to the
    shared ladder above.
    """

    engine: str
    rule_id: str
    severity: str
    message: str
    line: Optional[int] = None
    snippet: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "engine": self.engine,
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.message,
            "line": self.line,
            "snippet": self.snippet,
        }


class SastEngine(ABC):
    """Uniform interface over an external static-analysis tool."""

    #: short, stable identifier used in config/requests (e.g. "bandit").
    name: str = ""

    #: languages this engine can analyze (lowercase). Empty => any.
    languages: tuple = ()

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the underlying tool is installed and runnable."""
        raise NotImplementedError

    def supports(self, language: Optional[str]) -> bool:
        """Return True if this engine analyzes ``language``.

        An engine with no declared languages is treated as language-agnostic.
        Unknown/empty language defaults to supported so we still attempt a scan.
        """
        if not self.languages:
            return True
        if not language:
            return True
        return language.lower() in self.languages

    @abstractmethod
    def scan(
        self, code: str, *, filename: str, language: Optional[str] = None
    ) -> List[Finding]:
        """Scan a single code blob and return normalized findings.

        Implementations must never raise on "no findings"; an empty list means
        a clean scan. Raising is reserved for genuine engine failures.
        """
        raise NotImplementedError

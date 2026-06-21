"""Source-agnostic interface and result shape for skill background gathering.

A *source* knows how to gather background for an origin of a particular kind
(GitHub today; other forges could be added). The normalized result is a
``Background`` object whose five sections map 1:1 to the "top 5" pieces of
information requested for an import trust decision:

    1. provenance  - where it came from (repo/ref/path pinned to a commit)
    2. publisher   - who published it and how reputable the source is
    3. license     - whether it is legally safe to use / redistribute
    4. integrity   - whether the bytes are genuine / unmodified
    5. behavior    - what the skill reaches out to or runs

plus a rolled-up ``confidence`` of "high" | "medium" | "low".
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"

# License categories used for the legality read-out.
LICENSE_PERMISSIVE = "permissive"
LICENSE_COPYLEFT = "copyleft"
LICENSE_NONE = "none"
LICENSE_UNKNOWN = "unknown"

# Coarse SPDX -> category map for the common cases. Anything not listed and not
# empty is reported as "unknown" so the user still sees the raw SPDX id.
_PERMISSIVE_SPDX = {
    "MIT", "APACHE-2.0", "BSD-2-CLAUSE", "BSD-3-CLAUSE", "ISC", "0BSD",
    "UNLICENSE", "MPL-2.0", "ZLIB", "PYTHON-2.0",
}
_COPYLEFT_SPDX = {
    "GPL-2.0", "GPL-3.0", "GPL-2.0-ONLY", "GPL-3.0-ONLY", "GPL-2.0-OR-LATER",
    "GPL-3.0-OR-LATER", "LGPL-2.1", "LGPL-3.0", "AGPL-3.0", "AGPL-3.0-ONLY",
    "AGPL-3.0-OR-LATER",
}


def license_category(spdx_id: Optional[str]) -> str:
    """Classify an SPDX id into a coarse legality category.

    Empty / missing -> "none"; recognized permissive/copyleft -> that category;
    anything else (incl. GitHub's "NOASSERTION") -> "unknown".
    """
    if not spdx_id:
        return LICENSE_NONE
    key = spdx_id.strip().upper()
    if key in ("", "NOASSERTION"):
        return LICENSE_UNKNOWN if key == "NOASSERTION" else LICENSE_NONE
    if key in _PERMISSIVE_SPDX:
        return LICENSE_PERMISSIVE
    if key in _COPYLEFT_SPDX:
        return LICENSE_COPYLEFT
    return LICENSE_UNKNOWN


@dataclass
class Background:
    """Normalized "background" for a skill, across the five trust dimensions.

    Every section is a plain dict so the whole object serializes cleanly for
    the generic plugin UI and for storage in a skill's ``extra`` field. Each
    section carries a ``status`` ("ok" | "unavailable" | "error") so a partial
    failure (e.g. GitHub rate-limited the license call) degrades gracefully
    rather than failing the whole gather.
    """

    source: str = ""
    provenance: Dict[str, Any] = field(default_factory=dict)
    publisher: Dict[str, Any] = field(default_factory=dict)
    license: Dict[str, Any] = field(default_factory=dict)
    integrity: Dict[str, Any] = field(default_factory=dict)
    behavior: Dict[str, Any] = field(default_factory=dict)
    confidence: str = CONFIDENCE_LOW
    confidence_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "confidence": self.confidence,
            "confidence_reasons": self.confidence_reasons,
            "provenance": self.provenance,
            "publisher": self.publisher,
            "license": self.license,
            "integrity": self.integrity,
            "behavior": self.behavior,
        }


class ProvenanceSource(ABC):
    """Gathers background for origins of a particular kind (e.g. GitHub)."""

    #: short, stable identifier (e.g. "github").
    name: str = ""

    @abstractmethod
    def matches(self, origin: Dict[str, Any]) -> bool:
        """Return True if this source can handle ``origin`` (by type/url)."""
        raise NotImplementedError

    @abstractmethod
    def gather(self, origin: Dict[str, Any]) -> Background:
        """Gather background for ``origin``.

        Implementations must not raise for *expected* remote failures (rate
        limit, 404, network) — they record a per-section ``status`` instead and
        return a partial ``Background``. Raising is reserved for programmer
        errors (e.g. an origin this source does not match).
        """
        raise NotImplementedError

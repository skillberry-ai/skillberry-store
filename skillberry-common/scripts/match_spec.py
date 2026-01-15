"""
match_spec.py

Implements match_spec(spec, current_version) and provides a tiny CLI:

Usage:
  python match_spec.py <spec> <major>.<minor>.<micro>

Exit codes:
  0 => match
  1 => no match (or invalid spec; prints warning to stderr)
"""

from __future__ import annotations
import sys
import re
from typing import Tuple


def match_spec(spec: str, current: str) -> bool:
    """
    Match a version spec against current (major.minor.micro).

    Spec grammar:
      - Components: 1..3 dot-separated integers: X | X.Y | X.Y.Z
      - Optional '+' suffix allowed on any spec: X+ | X.Y+ | X.Y.Z+
        Meaning:
          X+        => major >= X
          X.Y+      => major == X AND minor >= Y
          X.Y.Z+    => major == X AND minor == Y AND micro >= Z
      - Without '+', match exactly up to given specificity:
          X         => major == X
          X.Y       => major == X AND minor == Y
          X.Y.Z     => major == X AND minor == Y AND micro == Z
    """
    spec = spec.strip()
    plus = spec.endswith("+")
    if plus:
        spec = spec[:-1]

    parts = [int(p) for p in spec.split(".")]
    cparts = [int(p) for p in current.split(".")]

    for i in range(len(parts)):
        if i < (len(parts) - 1):
            if parts[i] != cparts[i]:
                return 1
        else:
            if plus:
                return parts[i] <= cparts[i]
            return parts[i] == cparts[i]

def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "WARNING: Usage: python match_spec.py <spec> <major>.<minor>.<micro>",
            file=sys.stderr,
        )
        return 1

    return 0 if match_spec(argv[1], argv[2]) else 1

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

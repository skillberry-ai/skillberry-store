"""Hypothesis-backed input generator (one engine implementing InputGenerator).

Draws values from Hypothesis strategies mapped from each parameter's declared
type, plus missing-required cases. Deterministic via a fixed ``@seed`` + ``@given``
harness (the supported way to run Hypothesis outside pytest). Optional: if the
``hypothesis`` package is absent, :meth:`is_available` is False and the DAST
scanner reports disabled.
"""

from __future__ import annotations

import importlib.util
from typing import Any, Dict, List

from .base import InputGenerator

_MODULE = "hypothesis"
_DRAWS_PER_PARAM = 4


class HypothesisGenerator(InputGenerator):
    name = "hypothesis"

    def is_available(self) -> bool:
        return importlib.util.find_spec(_MODULE) is not None

    def install_hint(self) -> str:
        return (
            f"install e.g. `pip install {_MODULE}` or "
            f"`pip install 'skillberry-plugin-dast[{self.name}]'`"
        )

    # ── strategy mapping + deterministic draw ────────────────────────────────

    def _strategy_for(self, param_type: Any):
        from hypothesis import strategies as st

        t = (param_type or "").lower() if isinstance(param_type, str) else ""
        if t in ("string", "str"):
            return st.text()
        if t in ("integer", "int"):
            return st.integers()
        if t in ("number", "float"):
            return st.floats(allow_nan=True, allow_infinity=True)
        if t in ("boolean", "bool"):
            return st.booleans()
        if t in ("array", "list"):
            return st.lists(st.text(), max_size=5)
        if t in ("object", "dict"):
            return st.dictionaries(st.text(max_size=8), st.text(max_size=8), max_size=5)
        return st.one_of(st.text(), st.integers(), st.booleans(), st.none())

    def _draw(self, strategy, n: int, seed: int) -> List[Any]:
        from hypothesis import HealthCheck, given
        from hypothesis import seed as hypo_seed
        from hypothesis import settings

        collected: List[Any] = []

        @hypo_seed(seed)
        @settings(
            max_examples=n * 8,
            database=None,
            deadline=None,
            suppress_health_check=list(HealthCheck),
        )
        @given(strategy)
        def _collect(value):
            if len(collected) < n and value not in collected:
                collected.append(value)

        try:
            _collect()
        except Exception:
            pass
        return collected[:n]

    # ── InputGenerator contract ──────────────────────────────────────────────

    def generate_cases(
        self, params: Dict[str, Any], *, seed: int = 1729, max_cases: int = 24
    ) -> List[Dict[str, Any]]:
        properties: Dict[str, Any] = params.get("properties") or {}
        required = set(params.get("required") or [])
        names = list(properties.keys())

        if not names:
            return [{"label": "no-args", "args": {}}]

        cases: List[Dict[str, Any]] = []

        base_args: Dict[str, Any] = {}
        for i, name in enumerate(names):
            ptype = (properties.get(name) or {}).get("type")
            drawn = self._draw(self._strategy_for(ptype), 1, seed + i)
            base_args[name] = drawn[0] if drawn else None
        cases.append({"label": "baseline", "args": dict(base_args)})

        for i, name in enumerate(names):
            ptype = (properties.get(name) or {}).get("type")
            for j, value in enumerate(
                self._draw(
                    self._strategy_for(ptype), _DRAWS_PER_PARAM, seed + 100 * (i + 1)
                )
            ):
                args = dict(base_args)
                args[name] = value
                cases.append({"label": f"draw:{name}:{j}", "args": args})

        for name in sorted(required):
            args = {k: v for k, v in base_args.items() if k != name}
            cases.append({"label": f"missing-required:{name}", "args": args})

        return cases[:max_cases]

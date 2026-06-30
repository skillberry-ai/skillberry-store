"""Input-generator engine interface.

A generator turns a parameter schema (or a bare signature) into a deterministic
list of adversarial input *cases*. The engine is optional and pluggable, exactly
like the SAST plugin's scan engines: implement this interface, register the class
in ``generators/__init__.py``, and it becomes selectable — no change to the DAST
plugin core, which only consumes the neutral case shape below.

Case shape (engine-neutral, already what the runner consumes):
    {"label": str, "args": {param_name: value, ...}}
"""

from __future__ import annotations

from typing import Any, Dict, List


class InputGenerator:
    """Base class an input-generation engine implements."""

    #: Short identifier, e.g. "hypothesis". Used for registry + DAST_GENERATOR.
    name = "base"

    def is_available(self) -> bool:
        """True if this engine's dependency is installed and usable."""
        raise NotImplementedError

    def install_hint(self) -> str:
        """Human-readable hint for enabling this engine when unavailable."""
        return f"install the {self.name!r} input-generator engine"

    def generate_cases(
        self, params: Dict[str, Any], *, seed: int = 1729, max_cases: int = 24
    ) -> List[Dict[str, Any]]:
        """Produce a deterministic list of ``{label, args}`` cases.

        ``params`` is ``{properties: {name: {type}}, required: [...], optional:
        [...]}``. Implementations MUST be deterministic for a given ``seed`` and
        return at most ``max_cases`` cases. An entry point with no parameters
        should yield a single ``{"label": "no-args", "args": {}}`` case.
        """
        raise NotImplementedError

    def cases_from_signature(
        self, signature: List[str], *, seed: int = 1729, max_cases: int = 24
    ) -> List[Dict[str, Any]]:
        """Build cases from a bare parameter-name list (Tier-2 callables).

        Default: treat every name as a required, unknown-typed parameter and
        delegate to :meth:`generate_cases`. Engines may override.
        """
        params = {
            "properties": {name: {} for name in signature},
            "required": list(signature),
            "optional": [],
        }
        return self.generate_cases(params, seed=seed, max_cases=max_cases)

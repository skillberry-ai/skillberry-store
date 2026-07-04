"""Ensure the plugin package under `src/` is importable when the package
isn't installed into the active virtualenv, and stub optional runtime deps."""

import sys
import types
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Stub optional runtime deps that only exist when runspace-agent is installed.
if "claude_code_sdk" not in sys.modules:
    stub = types.ModuleType("claude_code_sdk")

    class ClaudeCodeOptions:  # noqa: D401 - trivial stub for tests
        """Minimal stand-in that just captures its kwargs."""

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    stub.ClaudeCodeOptions = ClaudeCodeOptions
    sys.modules["claude_code_sdk"] = stub

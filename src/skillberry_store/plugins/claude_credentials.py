"""Shared Claude Code credential/env resolution for runspace-backed plugins.

Reads the standard Claude Code ~/.claude/settings.json "env" block and the
process ANTHROPIC_*/CLAUDE_* variables. No legacy flat keys.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

logger = logging.getLogger(__name__)


def load_claude_settings() -> Optional[dict]:
    """Load ~/.claude/settings.json, or None if missing/unreadable."""
    settings_path = Path.home() / ".claude" / "settings.json"
    if not settings_path.exists():
        return None
    try:
        with open(settings_path, "r") as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001 - settings are best-effort
        logger.warning("Failed to load Claude settings from %s: %s", settings_path, e)
        return None


def settings_env(settings: Optional[dict]) -> Dict[str, str]:
    """Return the standard Claude Code ``env`` block, or {}."""
    if not settings:
        return {}
    env = settings.get("env")
    return env if isinstance(env, dict) else {}


def has_api_access(source: Mapping[str, Any]) -> bool:
    """True if ``source`` carries Anthropic API credentials."""
    if source.get("ANTHROPIC_API_KEY"):
        return True
    if source.get("ANTHROPIC_BASE_URL") and source.get("ANTHROPIC_AUTH_TOKEN"):
        return True
    return False


def build_agent_env(
    settings: Optional[dict], override: Optional[Dict[str, str]] = None
) -> Dict[str, str]:
    """Build the agent environment (lowest -> highest priority):

    1. The entire settings.json ``env`` block.
    2. Process ANTHROPIC_*/CLAUDE_* variables.
    3. ``override`` (per-run).
    """
    env: Dict[str, str] = {}
    for key, value in settings_env(settings).items():
        if value is not None:
            env[key] = str(value)
    for key, value in os.environ.items():
        if value and (key.startswith("ANTHROPIC_") or key.startswith("CLAUDE_")):
            env[key] = value
    if override:
        env.update(override)
    return env

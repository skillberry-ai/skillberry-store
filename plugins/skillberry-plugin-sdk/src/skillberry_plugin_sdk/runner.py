"""Uvicorn launcher for a plugin subclass of PluginLifecycleBase."""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Type

import uvicorn

from skillberry_plugin_sdk.lifecycle import PluginLifecycleBase

logger = logging.getLogger(__name__)


def run(plugin_cls: Type[PluginLifecycleBase]) -> None:
    """Bootstrap the plugin: validate env, build app, run uvicorn.

    Env consumed:
      SKILLBERRY_PLUGIN_PORT   — required; port to bind on 127.0.0.1
      SKILLBERRY_STORE_URL     — SBS base URL
      SKILLBERRY_STORE_TOKEN   — per-plugin bearer token
      SKILLBERRY_EVENTS_URL    — SSE endpoint base (defaults to STORE_URL)
    """
    plugin = plugin_cls()

    missing = plugin.validate_env()
    if missing:
        json.dump({"error": "missing_env", "missing": missing}, sys.stderr)
        sys.stderr.write("\n")
        sys.stderr.flush()
        sys.exit(2)

    port_env = os.environ.get("SKILLBERRY_PLUGIN_PORT")
    if not port_env:
        sys.stderr.write("SKILLBERRY_PLUGIN_PORT is required\n")
        sys.exit(3)
    try:
        port = int(port_env)
    except ValueError:
        sys.stderr.write(f"SKILLBERRY_PLUGIN_PORT is not an integer: {port_env}\n")
        sys.exit(3)

    app = plugin.build_app()
    logging.basicConfig(
        level=os.environ.get("PLUGIN_LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        log_level=os.environ.get("PLUGIN_UVICORN_LOG_LEVEL", "info"),
    )

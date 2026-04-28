"""Runspace plugin routes.

Hosts the three endpoints that previously lived in skills_api.py:

- POST /skills/{name}/export-agent-request — build a RunspaceAgent request
  for agentic export of a skill.
- GET  /ai-settings                        — load plugin settings (runspace
  URL, default env vars).
- PUT  /ai-settings                        — persist plugin settings.
- POST /agent/store-request                — build a RunspaceAgent request
  for the Store Agent, preloaded with store MCP + merged env vars.

Settings are stored at `$SBS_BASE_DIR/plugins/runspace/settings.json`, with
a one-time migration from `$SBS_BASE_DIR/ai_features/settings.json` the
first time the plugin loads.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from typing import Annotated, Any, Dict

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from skillberry_store.fast_api.skill_export_utils import get_skill_export_data
from skillberry_store.tools.configure import (
    get_ai_features_directory,
    get_plugin_directory,
)

from .agentic_exporter import build_agent_request, build_default_env
from .store_agent_builder import build_store_agent_request

logger = logging.getLogger(__name__)

PLUGIN_ID = "runspace"
_SETTINGS_FILENAME = "settings.json"


def _settings_path() -> str:
    return os.path.join(get_plugin_directory(PLUGIN_ID), _SETTINGS_FILENAME)


def _legacy_settings_path() -> str:
    return os.path.join(get_ai_features_directory(), "settings.json")


def migrate_legacy_settings() -> None:
    """One-time copy of the old ai_features/settings.json into the plugin dir.

    Safe to call repeatedly; becomes a no-op once the new file exists.
    """
    new = _settings_path()
    if os.path.exists(new):
        return
    old = _legacy_settings_path()
    if not os.path.exists(old):
        return
    try:
        os.makedirs(os.path.dirname(new), exist_ok=True)
        shutil.copy2(old, new)
        logger.info(f"Migrated runspace settings from {old} to {new}")
    except Exception as e:
        logger.warning(f"Failed to migrate runspace settings: {e}")


def build_router(app_settings_provider) -> APIRouter:
    """Return the runspace APIRouter.

    `app_settings_provider` is a zero-arg callable that returns the SBS
    settings object, used to resolve `agent_mcp_port` when building a
    Store Agent request. This keeps the plugin loosely coupled to the app.
    """
    migrate_legacy_settings()

    router = APIRouter()

    @router.post("/skills/{name}/export-agent-request")
    async def export_agent_request(name: str) -> Dict[str, Any]:
        logger.info(f"Request to build agentic export for skill: {name}")
        try:
            skill_dict, tools, snippets, tool_modules, _mcp_servers = get_skill_export_data(name)
            # The agentic exporter does not (yet) bundle MCP server configs
            # into the runspace agent context; the value is unpacked for
            # signature-compat with `get_skill_export_data` and discarded.
            request_body = build_agent_request(
                skill_dict=skill_dict,
                tools=tools,
                snippets=snippets,
                tool_modules=tool_modules,
            )
            return request_body
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error building agentic export for skill '{name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error building agentic export: {str(e)}"
            )

    @router.get("/ai-settings")
    async def get_ai_settings() -> Dict[str, Any]:
        path = _settings_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read runspace settings file: {e}")
        return {
            "runspace_url": "http://localhost:6767",
            "env_vars": [
                {"key": k, "value": v}
                for k, v in build_default_env().items()
            ],
        }

    @router.put("/ai-settings")
    async def save_ai_settings(request: Request) -> Dict[str, str]:
        path = _settings_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = await request.json()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return {"message": "Settings saved"}

    @router.post("/agent/store-request")
    async def build_store_agent_request_endpoint(
        prompt: Annotated[str, Form()],
        context_files: list[UploadFile] = File(default=[]),
    ) -> Dict[str, Any]:
        if not prompt:
            raise HTTPException(status_code=400, detail="'prompt' field is required")

        settings = app_settings_provider()
        agent_mcp_port = getattr(settings, "agent_mcp_port", 9999)
        request_body = build_store_agent_request(prompt, agent_mcp_port=agent_mcp_port)

        context_dir = request_body.get("context_dir", "")
        for upload in context_files:
            if upload.filename:
                dest = os.path.join(context_dir, upload.filename)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                content = await upload.read()
                with open(dest, "wb") as f:
                    f.write(content)

        path = _settings_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    ai_settings = json.load(f)
                env_vars = ai_settings.get("env_vars", [])
                env_dict: Dict[str, str] = {}
                for ev in env_vars:
                    k, v = ev.get("key", ""), ev.get("value", "")
                    if k and v and not (v.startswith("<") and v.endswith(">")):
                        env_dict[k] = v
                if env_dict:
                    request_body["agent_settings"]["env"].update(env_dict)
                runspace_url = ai_settings.get("runspace_url")
                if runspace_url:
                    request_body["_runspace_url"] = runspace_url
            except Exception as e:
                logger.warning(f"Failed to merge runspace settings: {e}")

        return request_body

    return router

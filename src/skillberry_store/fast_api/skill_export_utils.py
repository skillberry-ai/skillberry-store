"""Shared helpers for assembling skill export payloads.

Used by both the core Anthropic-zip exporter (skills_api.py) and the
runspace plugin's agentic exporter.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Tuple

from fastapi import HTTPException

from skillberry_store.modules.file_handler import FileHandler
from skillberry_store.tools.configure import (
    get_external_mcps_directory,
    get_files_directory_path,
    get_skills_directory,
    get_snippets_directory,
    get_tools_directory,
)

logger = logging.getLogger(__name__)


def get_skill_export_data(
    name: str,
) -> Tuple[
    Dict[str, Any],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    Dict[str, str],
    List[Dict[str, Any]],
]:
    """Gather a skill's dict, tools, snippets, tool module source, and
    external MCP server configs required by any tool in the skill.

    Returns:
        (skill_dict, tools, snippets, tool_modules, mcp_servers)
        The `mcp_servers` list is the raw persisted config entries (secrets
        intact) for every server referenced via `tool.mcp_dependencies` or
        `tool.mcp_server`. The exporter is responsible for redacting before
        bundling into a shareable ZIP.

    Raises HTTPException(404) if the skill is missing; HTTPException(500)
    for other failures.
    """
    skill_handler = FileHandler(get_skills_directory())
    tools_handler = FileHandler(get_tools_directory())
    snippets_handler = FileHandler(get_snippets_directory())
    files_handler = FileHandler(get_files_directory_path())

    skill_filename = f"{name}.json"
    try:
        content = skill_handler.read_file(skill_filename, raw_content=True)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    if not isinstance(content, str):
        raise HTTPException(
            status_code=500, detail=f"Invalid content type for skill '{name}'"
        )
    skill_dict = json.loads(content)

    tools: List[Dict[str, Any]] = []
    tool_modules: Dict[str, str] = {}
    if skill_dict.get("tool_uuids"):
        for tool_uuid in skill_dict["tool_uuids"]:
            for filename in tools_handler.list_files():
                if not filename.endswith(".json"):
                    continue
                try:
                    tool_content = tools_handler.read_file(filename, raw_content=True)
                    if not isinstance(tool_content, str):
                        continue
                    tool_dict = json.loads(tool_content)
                    if tool_dict.get("uuid") != tool_uuid:
                        continue
                    tools.append(tool_dict)
                    tool_name = tool_dict["name"]
                    module_filename = tool_dict.get("module_name")
                    if not module_filename:
                        lang = tool_dict.get("programming_language", "python").lower()
                        ext = ".py" if lang == "python" else ".sh"
                        module_filename = f"{tool_name}{ext}"
                    try:
                        module_content = files_handler.read_file(
                            module_filename, raw_content=True
                        )
                        if isinstance(module_content, str):
                            tool_modules[tool_name] = module_content
                    except Exception as e:
                        logger.warning(
                            f"Could not read module for tool {tool_name}: {e}"
                        )
                    break
                except Exception as e:
                    logger.warning(f"Error reading tool file {filename}: {e}")

    snippets: List[Dict[str, Any]] = []
    if skill_dict.get("snippet_uuids"):
        for snippet_uuid in skill_dict["snippet_uuids"]:
            for filename in snippets_handler.list_files():
                if not filename.endswith(".json"):
                    continue
                try:
                    snippet_content = snippets_handler.read_file(filename, raw_content=True)
                    if not isinstance(snippet_content, str):
                        continue
                    snippet_dict = json.loads(snippet_content)
                    if snippet_dict.get("uuid") == snippet_uuid:
                        snippets.append(snippet_dict)
                        break
                except Exception as e:
                    logger.warning(f"Error reading snippet file {filename}: {e}")

    # Aggregate external-MCP configs referenced by any of the skill's tools.
    required_mcp_names: set = set()
    for t in tools:
        if t.get("mcp_server"):
            required_mcp_names.add(t["mcp_server"])
        for dep_name in (t.get("mcp_dependencies") or []):
            required_mcp_names.add(dep_name)
    mcp_servers: List[Dict[str, Any]] = []
    if required_mcp_names:
        try:
            mcps_handler = FileHandler(get_external_mcps_directory())
            for server_name in sorted(required_mcp_names):
                try:
                    raw = mcps_handler.read_file(f"{server_name}.json", raw_content=True)
                    if isinstance(raw, str):
                        mcp_servers.append(json.loads(raw))
                except Exception as e:
                    logger.warning(f"Skipping MCP '{server_name}' in export (missing or unreadable): {e}")
        except Exception as e:
            logger.warning(f"Could not enumerate external MCPs for export: {e}")

    return skill_dict, tools, snippets, tool_modules, mcp_servers

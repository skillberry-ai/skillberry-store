"""Curated Agent MCP Server for Skillberry Store.

Provides clean, well-named MCP tools for AI agents to manage the store.
Runs on its own port (default 9999) using FastMCP with SSE transport.
"""

import json
import logging
import socket
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware

from skillberry_store.modules.file_handler import FileHandler
from skillberry_store.modules.file_executor import FileExecutor
from skillberry_store.modules.description import Description
from skillberry_store.modules.external_mcp_manager import normalize_mcp_input
from skillberry_store.modules.tool_health import (
    find_dependents as _find_dependents,
    list_broken_tools as _list_broken_tools,
)
from skillberry_store.schemas.name_validation import validate_store_name_message
from skillberry_store.tools.configure import (
    get_tools_directory,
    get_files_directory_path,
    get_skills_directory,
    get_snippets_directory,
)

logger = logging.getLogger(__name__)


def create_agent_mcp_server(app, port: int = 9999):
    """Create and start the curated Agent MCP server.

    Args:
        app: The SBS FastAPI application instance (provides access to app.state).
        port: Port to run the MCP server on.

    Returns:
        The FastMCP server instance.
    """
    mcp = FastMCP(name="skillberry-agent", port=port)

    tool_handler = FileHandler(get_tools_directory())
    file_handler = FileHandler(get_files_directory_path())
    skill_handler = FileHandler(get_skills_directory())
    snippet_handler = FileHandler(get_snippets_directory())

    tools_descriptions: Optional[Description] = getattr(app.state, "tools_descriptions", None)

    # ---- Tool management ----

    @mcp.tool()
    def list_tools() -> str:
        """List all tools in the store with their name, description, and state."""
        tools = []
        for filename in tool_handler.list_files():
            if not filename.endswith(".json"):
                continue
            content = tool_handler.read_file(filename, raw_content=True)
            if isinstance(content, str):
                d = json.loads(content)
                tools.append({
                    "name": d.get("name"),
                    "description": d.get("description"),
                    "state": d.get("state"),
                    "version": d.get("version"),
                    "packaging_format": d.get("packaging_format"),
                    "tags": d.get("tags", []),
                })
        return json.dumps(tools, indent=2)

    @mcp.tool()
    def get_tool_metadata(name: str) -> str:
        """Get the full metadata manifest for a tool."""
        content = tool_handler.read_file(f"{name}.json", raw_content=True)
        if isinstance(content, str):
            return content
        return json.dumps({"error": f"Tool '{name}' not found"})

    @mcp.tool()
    def get_tool_code(name: str) -> str:
        """Get the Python source code of a tool."""
        content = tool_handler.read_file(f"{name}.json", raw_content=True)
        if not isinstance(content, str):
            return f"Error: Tool '{name}' not found"
        d = json.loads(content)
        module_name = d.get("module_name")
        if not module_name:
            return f"Error: Tool '{name}' has no module file"
        code = file_handler.read_file(module_name, raw_content=True)
        if isinstance(code, str):
            return code
        return f"Error: Could not read module file '{module_name}'"

    @mcp.tool()
    def update_tool_code(name: str, code: str) -> str:
        """Update the source code of a tool.

        Args:
            name: The tool name.
            code: The new Python source code.
        """
        content = tool_handler.read_file(f"{name}.json", raw_content=True)
        if not isinstance(content, str):
            return f"Error: Tool '{name}' not found"
        d = json.loads(content)
        if d.get("packaging_format") == "mcp":
            return "Error: Cannot update source code for MCP-packaged tools"

        # Dependent-safe guard — refuse if any other tool lists this one as a
        # dependency, since the new code could break those callers.
        dependents = _find_dependents(name, tool_handler)
        if dependents:
            return json.dumps({
                "error": "tool_has_dependents",
                "tool": name,
                "dependents": dependents,
                "suggestion": (
                    f"Tool '{name}' is used by the listed tools. Changing its "
                    "code would break them. Create a new tool with a different "
                    "name, or remove/update the dependents first."
                ),
            })

        module_name = d.get("module_name")
        if not module_name:
            return f"Error: Tool '{name}' has no module file"
        file_handler.write_file_content(module_name, code)
        d["modified_at"] = datetime.now(timezone.utc).isoformat()
        tool_handler.write_file_content(f"{name}.json", json.dumps(d, indent=4))
        return f"Source code for tool '{name}' updated successfully."

    @mcp.tool()
    def update_tool_metadata(
        name: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        state: Optional[str] = None,
        version: Optional[str] = None,
    ) -> str:
        """Selectively update metadata fields of a tool.

        Args:
            name: The tool name.
            description: New description (optional).
            tags: New tags list (optional).
            state: New state - one of unknown, new, checked, approved (optional).
            version: New version string (optional).
        """
        content = tool_handler.read_file(f"{name}.json", raw_content=True)
        if not isinstance(content, str):
            return f"Error: Tool '{name}' not found"
        d = json.loads(content)
        old_desc = d.get("description")
        if description is not None:
            d["description"] = description
        if tags is not None:
            d["tags"] = tags
        if state is not None:
            d["state"] = state
        if version is not None:
            d["version"] = version
        d["modified_at"] = datetime.now(timezone.utc).isoformat()
        tool_handler.write_file_content(f"{name}.json", json.dumps(d, indent=4))
        if tools_descriptions and description and description != old_desc:
            try:
                tools_descriptions.update_description(name, description)
            except Exception:
                try:
                    tools_descriptions.write_description(name, description)
                except Exception:
                    pass
        return f"Metadata for tool '{name}' updated successfully."

    @mcp.tool()
    def create_tool(name: str, code: str, description: str, tags: Optional[List[str]] = None) -> str:
        """Create a new tool from Python code.

        Args:
            name: The tool name.
            code: The Python source code.
            description: A description of what the tool does.
            tags: Optional list of tags.
        """
        tool_filename = f"{name}.json"
        if tool_filename in tool_handler.list_files():
            return f"Error: Tool '{name}' already exists"
        import uuid as uuid_mod
        module_name = f"{name}.py"
        manifest = {
            "name": name,
            "uuid": str(uuid_mod.uuid4()),
            "version": "1.0.0",
            "description": description,
            "state": "approved",
            "tags": tags or [],
            "extra": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "modified_at": datetime.now(timezone.utc).isoformat(),
            "module_name": module_name,
            "programming_language": "python",
            "packaging_format": "code",
            "params": {"type": "object", "properties": {}, "required": [], "optional": []},
            "returns": None,
            "dependencies": None,
        }
        file_handler.write_file_content(module_name, code)
        tool_handler.write_file_content(tool_filename, json.dumps(manifest, indent=4))
        if tools_descriptions:
            try:
                tools_descriptions.write_description(name, description)
            except Exception:
                pass
        return json.dumps({"message": f"Tool '{name}' created successfully.", "uuid": manifest["uuid"]})

    @mcp.tool()
    def execute_tool(name: str, parameters: Optional[Dict[str, Any]] = None) -> str:
        """Execute a tool by name with the provided parameters.

        Args:
            name: The tool name.
            parameters: Optional dictionary of parameters.
        """
        content = tool_handler.read_file(f"{name}.json", raw_content=True)
        if not isinstance(content, str):
            return f"Error: Tool '{name}' not found"
        d = json.loads(content)
        module_name = d.get("module_name")
        if not module_name:
            return f"Error: Tool '{name}' has no module file"
        try:
            executor = FileExecutor(get_files_directory_path())
            result = executor.execute_python_file(module_name, parameters or {})
            return json.dumps(result)
        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"

    @mcp.tool()
    def search_tools(query: str, max_results: int = 5) -> str:
        """Search for tools by semantic description.

        Args:
            query: The search query.
            max_results: Maximum number of results to return.
        """
        if not tools_descriptions:
            return json.dumps({"error": "Search not available — no description index configured"})
        try:
            results = tools_descriptions.search(query, max_results)
            return json.dumps(results, indent=2)
        except Exception as e:
            return f"Error searching tools: {str(e)}"

    # ---- Skill management ----

    @mcp.tool()
    def list_skills() -> str:
        """List all skills in the store."""
        skills = []
        for filename in skill_handler.list_files():
            if not filename.endswith(".json"):
                continue
            content = skill_handler.read_file(filename, raw_content=True)
            if isinstance(content, str):
                d = json.loads(content)
                skills.append({
                    "name": d.get("name"),
                    "description": d.get("description"),
                    "state": d.get("state"),
                    "version": d.get("version"),
                    "tags": d.get("tags", []),
                    "tool_uuids": d.get("tool_uuids", []),
                    "snippet_uuids": d.get("snippet_uuids", []),
                })
        return json.dumps(skills, indent=2)

    @mcp.tool()
    def get_skill(name: str) -> str:
        """Get a skill with its resolved tools and snippets."""
        content = skill_handler.read_file(f"{name}.json", raw_content=True)
        if not isinstance(content, str):
            return json.dumps({"error": f"Skill '{name}' not found"})
        d = json.loads(content)
        # Resolve tool names from UUIDs
        tools_list = []
        for uuid in d.get("tool_uuids", []):
            for tf in tool_handler.list_files():
                if not tf.endswith(".json"):
                    continue
                tc = tool_handler.read_file(tf, raw_content=True)
                if isinstance(tc, str):
                    td = json.loads(tc)
                    if td.get("uuid") == uuid:
                        tools_list.append({"name": td["name"], "description": td.get("description"), "uuid": uuid})
                        break
        d["tools"] = tools_list
        return json.dumps(d, indent=2)

    @mcp.tool()
    def create_skill(
        name: str,
        description: str,
        tool_names: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        from_mcps: Optional[List[str]] = None,
        from_mcps_mode: str = "bundled_related",
    ) -> str:
        """Create a new skill.

        Mirrors the Create Skill UI modal: you can either pass explicit
        `tool_names`, or specify `from_mcps` to bulk-add every tool that
        touches those external MCP server(s), or both (results are merged;
        duplicates are skipped).

        Args:
            name: The skill name.
            description: Description of the skill.
            tool_names: Optional list of tool names to include explicitly.
            tags: Optional list of tags.
            from_mcps: Optional list of external MCP server names. If given,
                every tool associated with those MCPs (per `from_mcps_mode`)
                is added in one step after the skill is created.
            from_mcps_mode: One of
                - 'primitives'       — only MCP primitives (tool.mcp_server in from_mcps)
                - 'related'          — primitives + every composite whose mcp_dependencies intersects from_mcps
                - 'bundled_related'  — same as 'related' but skips tools with bundled_with_mcps==False
                  (if you want those included, pick 'related' instead)
        """
        # Slug validation — names are used as URL segments and `claude mcp add
        # <name>` arguments, so enforce the Anthropic Agent Skills format.
        invalid_msg = validate_store_name_message(name, kind="skill")
        if invalid_msg is not None:
            return json.dumps({"error": invalid_msg})
        skill_filename = f"{name}.json"
        if skill_filename in skill_handler.list_files():
            return f"Error: Skill '{name}' already exists"
        if from_mcps and from_mcps_mode not in ("primitives", "related", "bundled_related"):
            return f"Error: from_mcps_mode must be one of primitives|related|bundled_related (got {from_mcps_mode!r})"

        import uuid as uuid_mod
        tool_uuids: List[str] = []
        if tool_names:
            for tn in tool_names:
                tc = tool_handler.read_file(f"{tn}.json", raw_content=True)
                if isinstance(tc, str):
                    td = json.loads(tc)
                    tool_uuids.append(td.get("uuid", ""))
                else:
                    return f"Error: Tool '{tn}' not found"

        # Bulk-add from MCPs (same logic as bulk_add_tools_from_mcps — we run
        # it here against the seed tool_uuids set before the skill is first
        # persisted, so duplicates against the `tool_names` list are skipped.)
        bulk_summary: Optional[Dict[str, Any]] = None
        if from_mcps:
            mcp_set = set(from_mcps)
            existing_uuids = set(tool_uuids)
            added: List[Dict[str, str]] = []
            skipped_duplicate: List[str] = []
            skipped_broken: List[Dict[str, str]] = []
            skipped_unbundled: List[str] = []
            for fname in tool_handler.list_files():
                if not fname.endswith(".json"):
                    continue
                try:
                    d = json.loads(tool_handler.read_file(fname, raw_content=True))
                except Exception:
                    continue
                tool_mcp = d.get("mcp_server")
                tool_deps = set(d.get("mcp_dependencies") or [])
                if not ((tool_mcp in mcp_set) or (tool_deps & mcp_set)):
                    continue
                if from_mcps_mode == "primitives" and tool_mcp not in mcp_set:
                    continue
                if from_mcps_mode == "bundled_related" and d.get("bundled_with_mcps") is False:
                    skipped_unbundled.append(d.get("name") or fname[:-5])
                    continue
                if d.get("state") == "broken":
                    skipped_broken.append({"name": d.get("name"), "reason": d.get("broken_reason") or "broken"})
                    continue
                if d.get("uuid") in existing_uuids:
                    skipped_duplicate.append(d.get("name") or fname[:-5])
                    continue
                existing_uuids.add(d["uuid"])
                added.append({"name": d["name"], "uuid": d["uuid"]})
            tool_uuids = sorted(existing_uuids)
            bulk_summary = {
                "requested_mcps": sorted(mcp_set),
                "mode": from_mcps_mode,
                "added": added,
                "skipped_duplicate": skipped_duplicate,
                "skipped_broken": skipped_broken,
                "skipped_unbundled": skipped_unbundled,
            }

        manifest = {
            "name": name,
            "uuid": str(uuid_mod.uuid4()),
            "version": "1.0.0",
            "description": description,
            "state": "approved",
            "tags": tags or [],
            "extra": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "modified_at": datetime.now(timezone.utc).isoformat(),
            "tool_uuids": tool_uuids,
            "snippet_uuids": [],
        }
        skill_handler.write_file_content(skill_filename, json.dumps(manifest, indent=4))
        response: Dict[str, Any] = {
            "message": f"Skill '{name}' created successfully.",
            "uuid": manifest["uuid"],
            "tool_count": len(tool_uuids),
        }
        if bulk_summary is not None:
            response["mcp_bulk_add"] = bulk_summary
        return json.dumps(response, indent=2)

    @mcp.tool()
    def add_tool_to_skill(skill_name: str, tool_name: str) -> str:
        """Add a tool to a skill by name.

        Args:
            skill_name: The skill name.
            tool_name: The tool name to add.
        """
        sc = skill_handler.read_file(f"{skill_name}.json", raw_content=True)
        if not isinstance(sc, str):
            return f"Error: Skill '{skill_name}' not found"
        tc = tool_handler.read_file(f"{tool_name}.json", raw_content=True)
        if not isinstance(tc, str):
            return f"Error: Tool '{tool_name}' not found"
        skill = json.loads(sc)
        tool_uuid = json.loads(tc).get("uuid", "")
        if tool_uuid in skill.get("tool_uuids", []):
            return f"Tool '{tool_name}' is already in skill '{skill_name}'"
        skill.setdefault("tool_uuids", []).append(tool_uuid)
        skill["modified_at"] = datetime.now(timezone.utc).isoformat()
        skill_handler.write_file_content(f"{skill_name}.json", json.dumps(skill, indent=4))
        return f"Tool '{tool_name}' added to skill '{skill_name}'."

    @mcp.tool()
    def remove_tool_from_skill(skill_name: str, tool_name: str) -> str:
        """Remove a tool from a skill by name.

        Args:
            skill_name: The skill name.
            tool_name: The tool name to remove.
        """
        sc = skill_handler.read_file(f"{skill_name}.json", raw_content=True)
        if not isinstance(sc, str):
            return f"Error: Skill '{skill_name}' not found"
        tc = tool_handler.read_file(f"{tool_name}.json", raw_content=True)
        if not isinstance(tc, str):
            return f"Error: Tool '{tool_name}' not found"
        skill = json.loads(sc)
        tool_uuid = json.loads(tc).get("uuid", "")
        uuids = skill.get("tool_uuids", [])
        if tool_uuid not in uuids:
            return f"Tool '{tool_name}' is not in skill '{skill_name}'"
        uuids.remove(tool_uuid)
        skill["modified_at"] = datetime.now(timezone.utc).isoformat()
        skill_handler.write_file_content(f"{skill_name}.json", json.dumps(skill, indent=4))
        return f"Tool '{tool_name}' removed from skill '{skill_name}'."

    # ---- VMCP Server management ----

    @mcp.tool()
    def create_vmcp_server(skill_name: str, port: Optional[int] = None) -> str:
        """Create and start a Virtual MCP Server for a skill.

        Args:
            skill_name: The skill to expose via MCP.
            port: Optional port number. If not specified, an available port is auto-selected.
        """
        sc = skill_handler.read_file(f"{skill_name}.json", raw_content=True)
        if not isinstance(sc, str):
            return f"Error: Skill '{skill_name}' not found"
        skill = json.loads(sc)
        vmcp_manager = getattr(app.state, "vmcp_server_manager", None)
        if not vmcp_manager:
            return "Error: VMCP server manager not available"

        tool_names: List[str] = []
        for tool_uuid in skill.get("tool_uuids", []):
            for filename in tool_handler.list_files():
                if not filename.endswith(".json"):
                    continue
                content = tool_handler.read_file(filename, raw_content=True)
                if isinstance(content, str):
                    td = json.loads(content)
                    if td.get("uuid") == tool_uuid:
                        tool_names.append(td.get("name"))
                        break

        snippet_names: List[str] = []
        for snippet_uuid in skill.get("snippet_uuids", []):
            for filename in snippet_handler.list_files():
                if not filename.endswith(".json"):
                    continue
                content = snippet_handler.read_file(filename, raw_content=True)
                if isinstance(content, str):
                    sd = json.loads(content)
                    if sd.get("uuid") == snippet_uuid:
                        snippet_names.append(sd.get("name"))
                        break

        try:
            server = vmcp_manager.add_server(
                name=skill_name,
                description=f"VMCP server for skill '{skill_name}'",
                port=port,
                tools=tool_names,
                snippets=snippet_names,
            )
            server_port = server.port if hasattr(server, "port") else port
            return json.dumps({
                "message": f"VMCP server '{skill_name}' created and started.",
                "port": server_port,
                "connect_command": f"claude mcp add {skill_name} -s user -t sse http://localhost:{server_port}/sse",
            })
        except Exception as e:
            return f"Error creating VMCP server: {str(e)}"

    # ---- External MCP server management ----

    @mcp.tool()
    async def add_external_mcp(config_json: str) -> str:
        """Register and start one or more external MCP servers from a config.

        Accepts any of the five supported shapes (Claude-Desktop-style
        `{"mcpServers": {...}}`, a bare name→entry dict, a list of entries, a
        single entry, or `{"source_url": "..."}`). For each server, the store
        starts the transport (stdio subprocess, SSE connection, or streamable
        HTTP session), lists its tools, and registers each as a primitive
        named `<server>__<remote_name>`.

        Args:
            config_json: JSON string in any of the five shapes above.
        """
        mgr = getattr(app.state, "external_mcp_manager", None)
        if mgr is None:
            return json.dumps({"error": "External MCP manager is not initialized"})
        try:
            data = json.loads(config_json)
        except Exception as e:
            return json.dumps({"error": f"invalid JSON: {e}"})
        try:
            entries = normalize_mcp_input(data)
        except ValueError as e:
            return json.dumps({"error": str(e)})
        results = []
        for entry in entries:
            try:
                res = await mgr.start(entry, persist=True)
            except Exception as e:  # noqa: BLE001
                res = {"name": entry.get("name"), "status": "error", "error": str(e)}
            results.append(res)
        return json.dumps({"count": len(results), "results": results}, indent=2)

    @mcp.tool()
    def list_external_mcps() -> str:
        """List registered external MCP servers with status, transport, and tool count."""
        mgr = getattr(app.state, "external_mcp_manager", None)
        if mgr is None:
            return json.dumps({"error": "External MCP manager is not initialized"})
        return json.dumps(mgr.list_servers(), indent=2)

    @mcp.tool()
    async def remove_external_mcp(name: str) -> str:
        """Stop and unregister an external MCP server; delete all its primitives.

        Composites that depended on those primitives are NOT deleted — the
        universal health pass will flag them `state="broken"` so you can
        inspect, fix, or delete them.

        Args:
            name: The external MCP server name.
        """
        mgr = getattr(app.state, "external_mcp_manager", None)
        if mgr is None:
            return json.dumps({"error": "External MCP manager is not initialized"})
        try:
            result = await mgr.remove(name)
            return json.dumps(result, indent=2)
        except Exception as e:  # noqa: BLE001
            return json.dumps({"error": str(e)})

    @mcp.tool()
    async def restart_external_mcp(name: str) -> str:
        """Restart an external MCP server and reconcile its primitives.

        Use when the upstream server has changed (new tools, schema updates)
        or after a transient network/process failure.

        Args:
            name: The external MCP server name.
        """
        mgr = getattr(app.state, "external_mcp_manager", None)
        if mgr is None:
            return json.dumps({"error": "External MCP manager is not initialized"})
        try:
            result = await mgr.restart(name)
            return json.dumps(result, indent=2)
        except Exception as e:  # noqa: BLE001
            return json.dumps({"error": str(e)})

    @mcp.tool()
    async def list_remote_external_mcp_tools(name: str) -> str:
        """Introspect tools exposed by a running external MCP server.

        Pass-through over `list_tools()` on the live session. Handy for
        previewing what a server offers before relying on its primitives.

        Args:
            name: The external MCP server name.
        """
        mgr = getattr(app.state, "external_mcp_manager", None)
        if mgr is None:
            return json.dumps({"error": "External MCP manager is not initialized"})
        try:
            tools = await mgr.list_remote_tools(name)
            return json.dumps(tools, indent=2, default=str)
        except Exception as e:  # noqa: BLE001
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def list_broken_tools() -> str:
        """List every tool currently in `state='broken'` with its broken_reason.

        Useful for agent-driven repair loops after an external MCP server's
        upstream changes (schema drift, tool removal, server unavailable).
        """
        return json.dumps(_list_broken_tools(tool_handler), indent=2)

    @mcp.tool()
    def set_tool_bundled_with_mcps(name: str, bundled: bool) -> str:
        """Toggle whether this tool is included by default when skills are
        built from its MCP server(s).

        Only meaningful for MCP primitives and composites that depend on MCPs.
        When `bundled=false`, the tool is skipped from bulk 'add all tools of
        MCP X' operations (it can still be added manually). Useful while
        optimizing an MCP: mark a noisy primitive as unbundled, then agent-built
        skills stop pulling it in automatically.

        Args:
            name: The tool name.
            bundled: Whether this tool should be included by default.
        """
        content = tool_handler.read_file(f"{name}.json", raw_content=True)
        if not isinstance(content, str):
            return json.dumps({"error": f"Tool '{name}' not found"})
        d = json.loads(content)
        if not (d.get("mcp_server") or d.get("mcp_dependencies")):
            return json.dumps({
                "error": (
                    f"Tool '{name}' has no MCP association. The bundled_with_mcps "
                    "flag is only meaningful for MCP primitives and composites "
                    "that depend on MCPs."
                ),
            })
        d["bundled_with_mcps"] = bool(bundled)
        d["modified_at"] = datetime.now(timezone.utc).isoformat()
        tool_handler.write_file_content(f"{name}.json", json.dumps(d, indent=4))
        return json.dumps({"name": name, "bundled_with_mcps": d["bundled_with_mcps"]})

    @mcp.tool()
    def bulk_add_tools_from_mcps(
        skill_name: str,
        mcps: List[str],
        mode: str = "bundled_related",
    ) -> str:
        """Add tools to a skill in bulk, based on which external MCP(s) they touch.

        Args:
            skill_name: Target skill.
            mcps: External MCP server names whose tools should be pulled in (non-empty).
            mode: One of
                - 'primitives'       — only MCP primitives (tool.mcp_server in mcps)
                - 'related'          — primitives + every composite whose mcp_dependencies intersects mcps
                - 'bundled_related'  — same as 'related' but skips tools with bundled_with_mcps==False
                  (if you want those included, use 'related' instead)

        Returns a JSON summary with added, skipped_duplicate, skipped_broken,
        skipped_unbundled lists.
        """
        if not mcps:
            return json.dumps({"error": "`mcps` must be non-empty"})
        if mode not in ("primitives", "related", "bundled_related"):
            return json.dumps({
                "error": f"`mode` must be one of primitives|related|bundled_related (got {mode!r})"
            })
        mcp_set = set(mcps)

        try:
            skill_raw = skill_handler.read_file(f"{skill_name}.json", raw_content=True)
        except Exception:
            return json.dumps({"error": f"Skill '{skill_name}' not found"})
        if not isinstance(skill_raw, str):
            return json.dumps({"error": f"Invalid content for skill '{skill_name}'"})
        skill_dict = json.loads(skill_raw)
        existing_uuids = set(skill_dict.get("tool_uuids") or [])

        added, skipped_duplicate, skipped_broken, skipped_unbundled = [], [], [], []
        for fname in tool_handler.list_files():
            if not fname.endswith(".json"):
                continue
            try:
                d = json.loads(tool_handler.read_file(fname, raw_content=True))
            except Exception:
                continue
            tool_mcp = d.get("mcp_server")
            tool_deps = set(d.get("mcp_dependencies") or [])
            if not ((tool_mcp in mcp_set) or (tool_deps & mcp_set)):
                continue
            if mode == "primitives" and tool_mcp not in mcp_set:
                continue
            if mode == "bundled_related" and d.get("bundled_with_mcps") is False:
                skipped_unbundled.append(d.get("name") or fname[:-5])
                continue
            if d.get("state") == "broken":
                skipped_broken.append({"name": d.get("name"), "reason": d.get("broken_reason") or "broken"})
                continue
            if d.get("uuid") in existing_uuids:
                skipped_duplicate.append(d.get("name") or fname[:-5])
                continue
            existing_uuids.add(d["uuid"])
            added.append({"name": d["name"], "uuid": d["uuid"]})

        if added:
            skill_dict["tool_uuids"] = sorted(existing_uuids)
            skill_dict["modified_at"] = datetime.now(timezone.utc).isoformat()
            skill_handler.write_file_content(
                f"{skill_name}.json", json.dumps(skill_dict, indent=4)
            )

        return json.dumps({
            "skill": skill_name,
            "mode": mode,
            "requested_mcps": sorted(mcp_set),
            "added": added,
            "skipped_duplicate": skipped_duplicate,
            "skipped_broken": skipped_broken,
            "skipped_unbundled": skipped_unbundled,
        }, indent=2)

    @mcp.tool()
    def get_tool_metrics(name: str) -> str:
        """Get execution metrics for a tool (count and latency).

        Args:
            name: The tool name.
        """
        try:
            from prometheus_client import REGISTRY
            metrics_data = {"tool": name, "execute_count": 0, "success_count": 0, "avg_latency_seconds": None}
            for metric in REGISTRY.collect():
                if "execute_tool_counter" in metric.name:
                    for sample in metric.samples:
                        if sample.labels.get("name") == name:
                            metrics_data["execute_count"] = int(sample.value)
                elif "execute_successfully_tool_counter" in metric.name:
                    for sample in metric.samples:
                        if sample.labels.get("name") == name:
                            metrics_data["success_count"] = int(sample.value)
                elif "execute_successfully_tool_latency" in metric.name and "_sum" in sample.name:
                    for sample in metric.samples:
                        if sample.labels.get("name") == name and "_sum" in sample.name:
                            total = sample.value
                            if metrics_data["success_count"] > 0:
                                metrics_data["avg_latency_seconds"] = round(total / metrics_data["success_count"], 4)
            return json.dumps(metrics_data, indent=2)
        except Exception as e:
            return f"Error getting metrics: {str(e)}"

    # ---- Start the server ----

    def _start():
        logger.info(f"Starting Agent MCP server on port {port}")
        sse_app = mcp.sse_app()
        sse_app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
            allow_credentials=True,
            expose_headers=["*"],
        )
        uvicorn.run(sse_app, host="127.0.0.1", port=port, log_level="info")

    server_thread = threading.Thread(target=_start, daemon=True)
    server_thread.start()

    logger.info(f"Agent MCP server started on port {port}")
    return mcp

"""Skillberry Plugin rossoctl Tools: skills whose tools are rossoctl tools.

Option 0 (docs/design/rossoctl-skills.md, r8). rossoctl is unchanged and
store core is unchanged except an independent bug fix. The plugin uses only
plugin routes and the StoreAPI, and creates ordinary store objects:

* one **code** tool per MCP tool of each imported rossoctl tool, whose module
  is a generated proxy (store-side execution through rossoctl ``/invoke``);
* optionally a skill, with an instructions snippet carrying a generated Tools
  section and a ``rossoctl-tools.json`` snippet;
* a **deployment recipe**: the rossoctl ``POST /api/v1/agents`` body that links
  the skill and wires its tools as MCP (``MCP_URLS``), with a pre-flight check.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from skillberry_store.plugins.base import (
    PluginBase,
    PluginMetadata,
    PluginType,
    requires,
)

from . import proxy, recipe, skill as skill_mod
from .backend import (
    RossoctlBackend,
    RossoctlError,
    RossoctlNotFound,
    service_port,
    validate_label,
)

logger = logging.getLogger(__name__)

SLUG = "rossoctl-tools"
INSTRUCTIONS_SUFFIX = "-instructions"
TOOLS_JSON_SUFFIX = "-rossoctl-tools"


def _bearer(request) -> Optional[str]:
    """The caller's bearer, forwarded only in delegated deployments."""
    if os.getenv("ROSSOCTL_FORWARD_CALLER_TOKEN", "").lower() != "true":
        return None
    auth = request.headers.get("authorization") or ""
    return auth[7:].strip() if auth.lower().startswith("bearer ") else None


def _params(input_schema: Dict[str, Any]) -> Dict[str, Any]:
    s = input_schema or {}
    return {
        "type": "object",
        "properties": dict(s.get("properties") or {}),
        "required": list(s.get("required") or []),
    }


class SkillberryPluginRossoctlTools(PluginBase):
    """Use rossoctl tools in skills; generate the agent deployment that wires them."""

    def __init__(self, backend: Optional[RossoctlBackend] = None):
        super().__init__()
        self._metadata = PluginMetadata(
            name="rossoctl Tools",
            version="0.2.0",
            description="Compose skills from rossoctl tools and generate the rossoctl agent that uses them",
            plugin_type=PluginType.IMPORTER,
        )
        self.backend = backend or RossoctlBackend()

    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata

    def is_enabled(self) -> bool:
        return self.backend.configured

    def get_status_message(self) -> str:
        return (
            "Ready" if self.backend.configured else "Disabled: set ROSSOCTL_BACKEND_URL"
        )

    # ---- store helpers -------------------------------------------------------

    def _tools_by_name(self) -> Dict[str, Dict[str, Any]]:
        return {t["name"]: t for t in self.store.list_tools() if t.get("name")}

    def _skill_tools(self, skill: Dict[str, Any]) -> List[Dict[str, Any]]:
        tools = list(skill.get("tools") or [])
        if not tools:
            tools = [
                t
                for t in (self.store.get_tool(u) for u in skill.get("tool_uuids") or [])
                if t
            ]
        return tools

    def _get_skill(self, name_or_uuid: str) -> Dict[str, Any]:
        found = self.store.get_skill(name_or_uuid)
        if found is None:
            raise RossoctlNotFound(f"skill '{name_or_uuid}' not found")
        return found

    # ---- import --------------------------------------------------------------

    async def import_tools(
        self,
        namespace: str,
        refs: List[Dict[str, Any]],
        skill: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        bearer: Optional[str] = None,
    ) -> Dict[str, Any]:
        self.backend.check_namespace(namespace)
        existing = self._tools_by_name()
        created: List[Dict[str, Any]] = []
        errors: List[Dict[str, str]] = []
        taken: Dict[str, str] = {}  # store name -> rossoctl tool, within this import
        for ref in refs:
            tool_name = ref["name"]
            try:
                validate_label(tool_name, "tool name")
                detail = await self.backend.get_tool(
                    namespace, tool_name, bearer=bearer
                )
                port = service_port(detail)
                mcp_tools = await self.backend.connect(
                    namespace, tool_name, bearer=bearer
                )
            except RossoctlNotFound:
                errors.append(
                    {
                        "tool": tool_name,
                        "detail": f"tool '{tool_name}' not found in namespace '{namespace}'",
                    }
                )
                continue
            except (RossoctlError, ValueError) as e:
                errors.append({"tool": tool_name, "detail": str(e)})
                continue
            if not mcp_tools:
                errors.append(
                    {
                        "tool": tool_name,
                        "detail": "the tool's MCP server lists no tools",
                    }
                )
                continue
            read_only = set(ref.get("read_only") or [])
            for mt in mcp_tools:
                try:
                    created.append(
                        self._create_proxy(
                            namespace,
                            tool_name,
                            port,
                            ref.get("gateway_prefix"),
                            mt,
                            mt.get("name") in read_only,
                            tags or [],
                            existing,
                            taken,
                        )
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to import {tool_name}/{mt.get('name')}: {e}"
                    )
                    errors.append(
                        {"tool": tool_name, "detail": f"{mt.get('name')}: {e}"}
                    )
        skill_uuid = None
        if skill and created:
            skill_uuid = self._create_skill(skill, created, tags or [])
        return {
            "tools": [
                {
                    "uuid": t["uuid"],
                    "name": t["name"],
                    "rossoctl_tool": skill_mod.meta(t)["tool"],
                }
                for t in created
            ],
            "skill_uuid": skill_uuid,
            "errors": errors,
        }

    def _create_proxy(
        self,
        namespace,
        tool_name,
        port,
        gateway_prefix,
        mt,
        read_only,
        tags,
        existing,
        taken,
    ):
        mcp_name = mt["name"]
        store_name = proxy.python_name(mcp_name)
        owner = taken.get(store_name)
        if owner is None and store_name in existing:
            m = skill_mod.meta(existing[store_name])
            owner = m["tool"] if m else ""
        if owner is not None and owner != tool_name:  # D14: prefix on collision only
            store_name = proxy.python_name(f"{tool_name}__{mcp_name}")
        taken[store_name] = tool_name
        schema = mt.get("input_schema") or {"type": "object", "properties": {}}
        meta = {
            "tool": tool_name,
            "namespace": namespace,
            "port": port,
            "path": "/mcp",
            "mcp_tool_name": mcp_name,
            "read_only": bool(read_only),
            "input_schema_sha256": proxy.canonical_schema_sha256(schema),
            "generator_version": proxy.GENERATOR_VERSION,
        }
        if gateway_prefix:
            meta["gateway_prefix"] = gateway_prefix
        module = proxy.render(store_name, meta, schema, mt.get("description") or "")
        data = {
            "name": store_name,
            "description": mt.get("description")
            or f"{mcp_name} from rossoctl tool {tool_name}",
            "packaging_format": "code",
            "programming_language": "python",
            "params": _params(schema),
            "tags": list(
                dict.fromkeys(
                    [
                        "mcp",
                        skill_mod.PROXY_TAG,
                        f"rossoctl-tool:{tool_name}",
                        f"namespace:{namespace}",
                        *tags,
                    ]
                )
            ),
            "extra": {"rossoctl": meta},
            "dependencies": [],
        }
        return self.store.create_tool(
            data, module_content=module.encode(), module_filename=f"{store_name}.py"
        )

    def _create_skill(
        self, spec: Dict[str, Any], tools: List[Dict[str, Any]], tags: List[str]
    ) -> str:
        name = spec["name"]
        section = skill_mod.tools_section(tools)
        instructions = skill_mod.with_tools_section(
            spec.get("instructions") or f"# {name}\n\n{spec['description']}\n", section
        )
        instr = self.store.create_snippet(
            {
                "name": f"{name}{INSTRUCTIONS_SUFFIX}",
                "description": f"Instructions for {name}",
                "content": instructions,
                "tags": ["file:SKILL.md"],
                "content_type": "text/markdown",
            }
        )
        tj = self.store.create_snippet(
            {
                "name": f"{name}{TOOLS_JSON_SUFFIX}",
                "description": f"rossoctl tools required by {name}",
                "content": skill_mod.tools_json(tools),
                "tags": [f"file:{skill_mod.TOOLS_JSON_PATH}", "rossoctl-generated"],
                "content_type": "application/json",
            }
        )
        result = self.store.create_skill(
            {
                "name": name,
                "description": spec["description"],
                "tool_uuids": [t["uuid"] for t in tools],
                "snippet_uuids": [instr["uuid"], tj["uuid"]],
                "tags": list(
                    dict.fromkeys(["rossoctl", *(spec.get("tags") or []), *tags])
                ),
                "extra": {
                    "rossoctl": {"required_tools": skill_mod.required_tools(tools)}
                },
            }
        )
        return result["uuid"]

    # ---- refresh -------------------------------------------------------------

    def refresh(self, skill_ref: str) -> Dict[str, Any]:
        """Regenerate the Tools section and rossoctl-tools.json; a new skill version."""
        current = self._get_skill(skill_ref)
        tools = self._skill_tools(current)
        snippets = list(current.get("snippets") or [])
        if not snippets:
            snippets = [
                s
                for s in (
                    self.store.get_snippet(u)
                    for u in current.get("snippet_uuids") or []
                )
                if s
            ]
        new_uuids: List[str] = []
        have_json = False
        section = skill_mod.tools_section(tools)
        for sn in snippets:
            tags = sn.get("tags") or []
            if f"file:{skill_mod.TOOLS_JSON_PATH}" in tags:
                have_json = True
                new = self.store.create_snippet(
                    {**self._snippet_fields(sn), "content": skill_mod.tools_json(tools)}
                )
                new_uuids.append(new["uuid"])
            elif "file:SKILL.md" in tags and skill_mod.BEGIN in (
                sn.get("content") or ""
            ):
                new = self.store.create_snippet(
                    {
                        **self._snippet_fields(sn),
                        "content": skill_mod.with_tools_section(
                            sn.get("content") or "", section
                        ),
                    }
                )
                new_uuids.append(new["uuid"])
            else:
                new_uuids.append(sn["uuid"])
        if not have_json and skill_mod.proxy_tools(tools):
            new = self.store.create_snippet(
                {
                    "name": f"{current['name']}{TOOLS_JSON_SUFFIX}",
                    "description": f"rossoctl tools required by {current['name']}",
                    "content": skill_mod.tools_json(tools),
                    "tags": [f"file:{skill_mod.TOOLS_JSON_PATH}", "rossoctl-generated"],
                    "content_type": "application/json",
                }
            )
            new_uuids.append(new["uuid"])
        data = {
            k: v
            for k, v in current.items()
            if k
            not in ("uuid", "created_at", "modified_at", "parent", "tools", "snippets")
        }
        data["snippet_uuids"] = new_uuids
        extra = dict(data.get("extra") or {})
        extra["rossoctl"] = {
            **(extra.get("rossoctl") or {}),
            "required_tools": skill_mod.required_tools(tools),
        }
        data["extra"] = extra
        result = self.store.create_skill(data)
        return {
            "skill_uuid": result["uuid"],
            "required_tools": extra["rossoctl"]["required_tools"],
        }

    @staticmethod
    def _snippet_fields(sn: Dict[str, Any]) -> Dict[str, Any]:
        return {
            k: sn[k] for k in ("name", "description", "tags", "content_type") if k in sn
        }

    # ---- check ---------------------------------------------------------------

    async def check(
        self,
        skill_ref: Optional[str],
        tool_uuids: List[str],
        namespaces: List[str],
        bearer=None,
    ):
        tools: List[Dict[str, Any]] = []
        if skill_ref:
            tools.extend(self._skill_tools(self._get_skill(skill_ref)))
        for u in tool_uuids:
            t = self.store.get_tool(u)
            if t is None:
                raise RossoctlNotFound(f"tool '{u}' not found")
            tools.append(t)
        proxies = skill_mod.proxy_tools(tools)
        drift = []
        live: Dict[tuple, Dict[str, Any]] = {}
        for t in proxies:
            m = skill_mod.meta(t)
            key = (m["namespace"], m["tool"])
            entry = {
                "uuid": t["uuid"],
                "name": t["name"],
                "rossoctl_tool": m["tool"],
                "stored_sha256": m.get("input_schema_sha256"),
            }
            try:
                if key not in live:
                    live[key] = {
                        x["name"]: x
                        for x in await self.backend.connect(*key, bearer=bearer)
                    }
                lt = live[key].get(m["mcp_tool_name"])
                if lt is None:
                    entry.update(
                        {
                            "drift": True,
                            "error": "the tool no longer offers this MCP tool",
                        }
                    )
                else:
                    sha = proxy.canonical_schema_sha256(
                        lt.get("input_schema") or {"type": "object", "properties": {}}
                    )
                    entry.update(
                        {"live_sha256": sha, "drift": sha != entry["stored_sha256"]}
                    )
            except (RossoctlError, ValueError) as e:
                entry.update({"drift": None, "error": str(e)})
            drift.append(entry)
        required = skill_mod.required_tools(proxies)
        targets = namespaces or sorted(
            {skill_mod.meta(t)["namespace"] for t in proxies}
        )
        pre = {}
        for ns in targets:
            self.backend.check_namespace(ns)
            pre[ns] = await recipe.preflight(self.backend, ns, required, bearer=bearer)
        return {"tools": drift, "namespaces": pre}

    # ---- routes ----------------------------------------------------------------

    def get_router(self):
        from fastapi import APIRouter, HTTPException, Query, Request
        from pydantic import BaseModel, Field

        router = APIRouter()

        class ToolRef(BaseModel):
            name: str
            read_only: List[str] = Field(default_factory=list)
            gateway_prefix: Optional[str] = None

        class SkillSpec(BaseModel):
            name: str
            description: str
            instructions: Optional[str] = None
            tags: List[str] = Field(default_factory=list)

        class ImportRequest(BaseModel):
            namespace: str
            tools: List[ToolRef]
            skill: Optional[SkillSpec] = None
            tags: List[str] = Field(default_factory=list)

        class AgentSpec(BaseModel):
            name: Optional[str] = None
            image: Optional[str] = None
            mode: str = "direct"

        class RecipeRequest(BaseModel):
            skill: str
            namespace: str
            agent: AgentSpec = Field(default_factory=AgentSpec)

        class CheckRequest(BaseModel):
            skill: Optional[str] = None
            tool_uuids: List[str] = Field(default_factory=list)
            namespaces: List[str] = Field(default_factory=list)

        class RefreshRequest(BaseModel):
            skill: str

        def http_error(e: Exception) -> HTTPException:
            if isinstance(e, ValueError):
                return HTTPException(status_code=400, detail=str(e))
            if isinstance(e, RossoctlError):
                return HTTPException(status_code=e.status_code, detail=str(e))
            return HTTPException(status_code=500, detail=str(e))

        @requires("tools", "list")
        @router.get("/tools")
        async def list_rossoctl_tools(request: Request, namespace: str = Query(...)):
            """rossoctl's tools in a namespace."""
            try:
                return {
                    "items": await self.backend.list_tools(
                        namespace, bearer=_bearer(request)
                    )
                }
            except (RossoctlError, ValueError) as e:
                raise http_error(e)

        @requires("tools", "create")
        @router.post("/import")
        async def import_rossoctl_tools(request: Request, body: ImportRequest):
            """Create proxy tools (and optionally a skill) from live rossoctl tools."""
            if not body.tools:
                raise HTTPException(status_code=400, detail="tools must not be empty")
            try:
                result = await self.import_tools(
                    body.namespace,
                    [t.model_dump() for t in body.tools],
                    skill=body.skill.model_dump() if body.skill else None,
                    tags=body.tags,
                    bearer=_bearer(request),
                )
            except (RossoctlError, ValueError) as e:
                raise http_error(e)
            if not result["tools"] and result["errors"]:
                all_missing = all("not found" in e["detail"] for e in result["errors"])
                raise HTTPException(
                    status_code=404 if all_missing else 502, detail=result["errors"]
                )
            return result

        @requires("skills", "get")
        @router.post("/recipe")
        async def deployment_recipe(request: Request, body: RecipeRequest):
            """The rossoctl agent-create request that links the skill and wires its tools."""
            try:
                found = self._get_skill(body.skill)
                tools = self._skill_tools(found)
                required = skill_mod.skill_required_tools(found, tools)
                if not required:
                    raise ValueError(f"skill '{found['name']}' has no rossoctl tools")
                return await recipe.build(
                    self.backend,
                    skill_name=found["name"],
                    required=required,
                    namespace=body.namespace,
                    agent_name=body.agent.name,
                    image=body.agent.image,
                    mode=body.agent.mode,
                    bearer=_bearer(request),
                )
            except (RossoctlError, ValueError) as e:
                raise http_error(e)

        @requires("tools", "list")
        @router.post("/check")
        async def check_rossoctl_tools(request: Request, body: CheckRequest):
            """Schema drift against the live tools, and per-namespace pre-flight. No writes."""
            try:
                return await self.check(
                    body.skill,
                    body.tool_uuids,
                    body.namespaces,
                    bearer=_bearer(request),
                )
            except (RossoctlError, ValueError) as e:
                raise http_error(e)

        @requires("skills", "create")
        @router.post("/refresh")
        async def refresh_skill(body: RefreshRequest):
            """Regenerate the skill's Tools section and rossoctl-tools.json."""
            try:
                return self.refresh(body.skill)
            except (RossoctlError, ValueError) as e:
                raise http_error(e)

        return router

    def get_cli_commands(self) -> Optional[Dict[str, Any]]:
        return None

    def get_ui_config(self) -> Optional[Dict[str, Any]]:
        return {
            "icon": "DownloadIcon",
            "color": "#B32FD8",
            "actions": [
                {
                    "label": "Import rossoctl tools",
                    "endpoint": f"/plugins/{SLUG}/import",
                    "method": "POST",
                    "params_schema": {
                        "type": "object",
                        "properties": {
                            "namespace": {
                                "type": "string",
                                "description": "rossoctl namespace, e.g. team1",
                            },
                            "tools": {
                                "type": "array",
                                "description": 'rossoctl tools, e.g. [{"name": "weather-tool", "read_only": ["get_weather"]}]',
                                "items": {
                                    "type": "object",
                                    "properties": {"name": {"type": "string"}},
                                    "required": ["name"],
                                },
                            },
                            "skill": {
                                "type": "object",
                                "description": "Optional skill to create",
                                "properties": {
                                    "name": {"type": "string"},
                                    "description": {"type": "string"},
                                    "instructions": {"type": "string"},
                                },
                            },
                        },
                        "required": ["namespace", "tools"],
                    },
                },
                {
                    "label": "Generate rossoctl agent",
                    "endpoint": f"/plugins/{SLUG}/recipe",
                    "method": "POST",
                    "params_schema": {
                        "type": "object",
                        "properties": {
                            "skill": {
                                "type": "string",
                                "description": "Skill name or uuid",
                            },
                            "namespace": {
                                "type": "string",
                                "description": "Namespace the agent will run in",
                            },
                            "agent": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "image": {"type": "string"},
                                    "mode": {
                                        "type": "string",
                                        "enum": ["direct", "gateway"],
                                    },
                                },
                            },
                        },
                        "required": ["skill", "namespace"],
                    },
                },
            ],
        }

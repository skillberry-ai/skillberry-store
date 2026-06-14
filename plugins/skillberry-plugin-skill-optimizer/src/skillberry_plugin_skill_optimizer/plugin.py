"""
Skillberry Plugin Skill Optimizer — optimizes existing skills using RunSpace.
"""

import asyncio
import json
import logging
import os
import shutil
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType
from skillberry_plugin_skill_optimizer.prompt import (
    REQUIRED_OUTPUTS_FILENAME,
    REQUIRED_OUTPUTS_TEMPLATE,
    build_runspace_prompt,
)

logger = logging.getLogger(__name__)

try:
    import runspace_agent
    from runspace_agent import RunspaceSession, run_agent
    from runspace_agent.workspaces import session_workspace
except ImportError:
    runspace_agent = None
    RunspaceSession = None
    run_agent = None
    session_workspace = None

try:
    from skillberry_store.tools.anthropic.importer import import_from_anthropic_skill
except ImportError:
    import_from_anthropic_skill = None

try:
    from skillberry_store.tools.anthropic.exporter import export_skill_to_directory
except ImportError:
    export_skill_to_directory = None


async def optimize_skill_session(prompt, skill_dir, context_dir, options, mode, plugin_instance):
    """Run a RunspaceSession to optimize a skill.

    Module-level so tests can patch it without reaching the real runspace layer.
    Returns the RunspaceSession result (with .session_id attribute).
    """
    gen_session_id = uuid.uuid4().hex[:12]
    workspace_root = session_workspace(gen_session_id)

    session = RunspaceSession(
        editable_dir=skill_dir,
        context_dir=context_dir,
        prompt=prompt,
        agent_options=options,
        preinstalled_skills=["skill-creator"],
        mode=mode,
    )

    t0 = time.monotonic()
    run_task = asyncio.create_task(run_agent(session, session_id=gen_session_id))
    progress_task = asyncio.create_task(
        plugin_instance._stream_progress(mode, workspace_root, run_task)
    )
    try:
        result = await run_task
    finally:
        progress_task.cancel()
        try:
            await progress_task
        except asyncio.CancelledError:
            pass

    elapsed = time.monotonic() - t0
    if not result.success:
        logger.error(
            f"Agent failed after {elapsed:.1f}s: "
            f"{result.agent_result.error or 'Unknown error'}"
        )
        raise RuntimeError(f"Agent failed: {result.agent_result.error or 'Unknown error'}")
    logger.info(
        f"Agent completed successfully in {elapsed:.1f}s "
        f"(session {result.session_id}, "
        f"{result.agent_result.total_tokens} tokens"
        + (f", ${result.agent_result.total_cost_usd:.4f}" if result.agent_result.total_cost_usd else "")
        + ")"
    )
    return result


class SkillberryPluginSkillOptimizer(PluginBase):
    """Plugin for optimizing existing Skillberry skills using RunSpace."""

    def __init__(self):
        super().__init__()

        self._metadata = PluginMetadata(
            name="Skill Optimizer",
            version="0.1.0",
            description="Optimize existing skills using RunSpace-powered Claude Code",
            plugin_type=PluginType.OPTIMIZER,
        )

        self._status_message = "Initializing..."
        self._runspace_available = False
        self._credentials_configured = False
        self._execution_mode = os.getenv("RUNSPACE_MODE", "container")
        self._claude_settings = None

        self._load_claude_settings()

        if runspace_agent is not None:
            try:
                self._runspace_available = True
                self._credentials_configured = self._check_credentials()

                if self._credentials_configured:
                    mode_label = f" ({self._execution_mode} mode)"
                    source = " from ~/.claude/settings.json" if self._claude_settings else ""
                    self._status_message = f"Ready{mode_label}{source}"
                else:
                    self._status_message = (
                        "Missing credentials: Set ANTHROPIC_API_KEY, "
                        "configure ~/.claude/settings.json, or provide "
                        "ANTHROPIC_BASE_URL + ANTHROPIC_AUTH_TOKEN"
                    )
            except Exception as e:
                self._status_message = f"Configuration error: {str(e)}"
                logger.error(f"Failed to initialize: {e}", exc_info=True)
        else:
            self._status_message = "Missing dependency: runspace-agent not installed"

    def _load_claude_settings(self):
        settings_path = Path.home() / ".claude" / "settings.json"
        if settings_path.exists():
            try:
                with open(settings_path, "r") as f:
                    self._claude_settings = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load Claude settings: {e}")

    def _check_credentials(self) -> bool:
        if os.getenv("ANTHROPIC_API_KEY"):
            return True
        if os.getenv("ANTHROPIC_BASE_URL") and os.getenv("ANTHROPIC_AUTH_TOKEN"):
            return True
        if self._claude_settings:
            if self._claude_settings.get("apiKey"):
                return True
            if self._claude_settings.get("baseUrl") and self._claude_settings.get("authToken"):
                return True
        return False

    def _build_claude_env(self, override_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        env = {}
        if self._claude_settings:
            if self._claude_settings.get("apiKey"):
                env["ANTHROPIC_API_KEY"] = self._claude_settings["apiKey"]
            if self._claude_settings.get("baseUrl"):
                env["ANTHROPIC_BASE_URL"] = self._claude_settings["baseUrl"]
            if self._claude_settings.get("authToken"):
                env["ANTHROPIC_AUTH_TOKEN"] = self._claude_settings["authToken"]
            if self._claude_settings.get("model"):
                env["ANTHROPIC_MODEL"] = self._claude_settings["model"]
        for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_MODEL"):
            val = os.getenv(var)
            if val:
                env[var] = val
        if override_env:
            env.update(override_env)
        return env

    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata

    def get_status_message(self) -> str:
        return self._status_message

    def is_enabled(self) -> bool:
        return self._runspace_available and self._credentials_configured

    def _stream_docker_logs(self, workspace_root: Path, stop: threading.Event) -> None:
        try:
            import docker
            client = docker.from_env()
            container = None
            for _ in range(60):
                if stop.is_set():
                    return
                time.sleep(0.5)
                for c in client.containers.list():
                    for mount in c.attrs.get("Mounts", []):
                        if str(workspace_root) in mount.get("Source", ""):
                            container = c
                            break
                    if container:
                        break
                if container:
                    break
            if not container:
                logger.debug("  [container] container not found within timeout")
                return
            cid = container.short_id
            logger.info(
                f"  [container] id={container.id}  short={cid}  workspace={workspace_root}\n"
                f"  [container] Live inspect: docker exec {cid} ls /workspace/agent_workspace/editable\n"
                f"  [container] NOTE: Claude runs in-memory — docker logs will be sparse until the "
                f"run completes, then conversation.json is written to {workspace_root}"
            )
            for chunk in container.logs(stream=True, follow=True, stderr=True, stdout=True):
                if stop.is_set():
                    break
                line = chunk.decode("utf-8", errors="replace").rstrip()
                if line:
                    logger.info(f"  [container:{cid}] {line}")
        except ImportError:
            logger.debug("Docker SDK not available")
        except Exception as e:
            logger.debug(f"Docker log streaming ended: {e}")

    def _replay_conversation(self, conv_path: Path) -> None:
        """Parse conversation.json and emit a full verbose log of every agent step."""
        try:
            conv = json.loads(conv_path.read_text(encoding="utf-8"))
            if not isinstance(conv, list):
                return
            logger.info(f"  [replay] conversation.json ready — {len(conv)} messages:")
            for msg in conv:
                msg_type = msg.get("type", "")
                data = msg.get("data", msg)
                if msg_type == "assistant":
                    for block in (data.get("content") or []):
                        if not isinstance(block, dict):
                            continue
                        if block.get("type") == "text":
                            text = block["text"].strip()
                            if text:
                                logger.info(f"  [agent] {text}")
                        elif block.get("type") == "tool_use":
                            tool_name = block.get("name", "?")
                            inp = block.get("input", {})
                            if "command" in inp:
                                detail = inp["command"]
                            elif "file_path" in inp or "path" in inp:
                                fpath = inp.get("file_path") or inp.get("path", "")
                                content_len = len(str(inp.get("content", "")))
                                detail = f"{fpath} ({content_len} chars)" if "content" in inp else fpath
                            else:
                                detail = json.dumps(inp, ensure_ascii=False)[:300]
                            logger.info(f"  [tool:{tool_name}] {detail}")
                elif msg_type == "tool":
                    content = data.get("content", "")
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                logger.info(f"  [result] {item['text'][:400]}")
                    elif content:
                        logger.info(f"  [result] {str(content)[:400]}")
                elif msg_type == "result":
                    turns = data.get("num_turns", "?")
                    cost = data.get("total_cost_usd")
                    usage = data.get("usage", {})
                    out_tok = usage.get("output_tokens", "?")
                    cache_r = usage.get("cache_read_input_tokens", 0)
                    cost_str = f" ${cost:.4f}" if cost is not None else ""
                    logger.info(
                        f"  [done] {turns} turns, {out_tok} output tokens"
                        f", {cache_r} cache-read tokens{cost_str}"
                    )
        except Exception as e:
            logger.debug(f"Could not replay conversation from {conv_path}: {e}")

    async def _stream_progress(self, mode: str, workspace_root: Path, run_task: "asyncio.Task") -> None:
        editable = workspace_root / "agent_workspace" / "editable"
        conv_path = workspace_root / "conversation.json"
        seen: set = set()
        conv_replayed = False
        stop = threading.Event()
        if mode == "container":
            t = threading.Thread(
                target=self._stream_docker_logs, args=(workspace_root, stop), daemon=True
            )
            t.start()
        try:
            while not run_task.done():
                await asyncio.sleep(5)
                # Poll editable/ for new files the agent is writing
                if editable.exists():
                    current = {str(p) for p in editable.rglob("*") if p.is_file()}
                    for f in sorted(current - seen):
                        logger.info(f"  [progress] created: {Path(f).relative_to(editable)}")
                    seen = current
                # conversation.json is written to the shared workspace volume just before
                # the container/process exits — replay it immediately when it appears
                if not conv_replayed and conv_path.exists():
                    conv_replayed = True
                    self._replay_conversation(conv_path)
        finally:
            stop.set()

    def _log_session_details(self, session_id: str) -> None:
        """Log session summary and (if not already replayed during streaming) conversation."""
        try:
            workspace = session_workspace(session_id)
            summary_path = workspace / "summary.md"
            if summary_path.exists():
                logger.info(f"Session summary:\n{summary_path.read_text(encoding='utf-8').strip()}")
            # conversation.json is replayed live in _stream_progress when it first appears;
            # replay again here only if the file wasn't caught during polling (e.g. very fast runs)
            conv_path = workspace / "conversation.json"
            if conv_path.exists():
                self._replay_conversation(conv_path)
        except Exception as e:
            logger.debug(f"Could not read session details for {session_id}: {e}")

    def _generate_output_skill_name(self, original_name: str, override: Optional[str] = None) -> str:
        """Generate the output skill name, appending numeric suffix if needed."""
        if override is not None:
            return override
        existing_names = {s["name"] for s in self.store.list_skills()}
        base = f"{original_name}_optimized"
        if base not in existing_names:
            return base
        i = 1
        while f"{base}({i})" in existing_names:
            i += 1
        return f"{base}({i})"

    async def optimize_skill(
        self,
        skill_uuid: str,
        output_skill_name: Optional[str] = None,
        include_metadata: bool = True,
        trajectories_dir: Optional[str] = None,
        additional_context_dir: Optional[str] = None,
        agent_env: Optional[Dict[str, str]] = None,
        execution_mode: Optional[str] = None,
        max_turns: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Optimize an existing skill and import the result as a new skill."""
        if not self._runspace_available:
            raise RuntimeError("runspace-agent not available")
        if export_skill_to_directory is None:
            raise RuntimeError("skillberry_store exporter not available")
        if import_from_anthropic_skill is None:
            raise RuntimeError("skillberry_store importer not available")
        if self._store_api is None:
            raise RuntimeError("Store API not available")
        if not self._credentials_configured and not agent_env:
            raise RuntimeError(
                "Anthropic credentials not configured. Set ANTHROPIC_API_KEY or provide agent_env"
            )

        skill = self.store.get_skill(skill_uuid)
        if skill is None:
            raise ValueError(f"Skill {skill_uuid!r} not found")

        if trajectories_dir and not Path(trajectories_dir).exists():
            raise ValueError(f"trajectories_dir does not exist: {trajectories_dir!r}")
        if additional_context_dir and not Path(additional_context_dir).exists():
            raise ValueError(f"additional_context_dir does not exist: {additional_context_dir!r}")

        original_name = skill["name"]
        logger.info(f"Optimizing skill '{original_name}' ({skill_uuid})...")

        from claude_code_sdk import ClaudeCodeOptions

        claude_env = self._build_claude_env(agent_env)
        options = ClaudeCodeOptions(
            env=claude_env,
            max_turns=max_turns or int(os.getenv("RUNSPACE_MAX_TURNS", "300")),
        )
        raw_mode = execution_mode or self._execution_mode
        mode: Literal["local", "container"] = "container" if raw_mode == "container" else "local"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            skill_dir = temp_path / "skill"
            skill_dir.mkdir()
            context_dir = temp_path / "context"
            context_dir.mkdir()

            tools = skill.get("tools", [])
            snippets = skill.get("snippets", [])
            tool_modules: Dict[str, str] = {}
            for tool in tools:
                if tool.get("module_name"):
                    try:
                        content = self.store.tools.read_file(
                            tool["uuid"], tool["module_name"], raw_content=True
                        )
                        tool_modules[tool["name"]] = content
                    except Exception as e:
                        logger.warning(f"Could not read module for tool '{tool['name']}': {e}")

            export_skill_to_directory(skill, tools, snippets, str(skill_dir), tool_modules)
            logger.info(f"Exported skill to {skill_dir}")

            (skill_dir / REQUIRED_OUTPUTS_FILENAME).write_text(
                json.dumps(REQUIRED_OUTPUTS_TEMPLATE, indent=2)
            )

            if include_metadata:
                metadata = {
                    "name": skill.get("name"),
                    "description": skill.get("description"),
                    "tags": skill.get("tags", []),
                    "extra": skill.get("extra", {}),
                    "tools": [
                        {"name": t.get("name"), "description": t.get("description")}
                        for t in tools
                    ],
                    "snippets": [
                        {"name": s.get("name"), "description": s.get("description")}
                        for s in snippets
                    ],
                }
                (context_dir / "skill_metadata.json").write_text(
                    json.dumps(metadata, indent=2)
                )

            if trajectories_dir:
                shutil.copytree(trajectories_dir, str(context_dir / "trajectories"))

            if additional_context_dir:
                shutil.copytree(additional_context_dir, str(context_dir / "additional_context"))

            prompt = build_runspace_prompt(
                has_metadata=include_metadata,
                has_trajectories=bool(trajectories_dir),
                has_additional_context=bool(additional_context_dir),
            )

            try:
                result = await optimize_skill_session(
                    prompt, skill_dir, context_dir, options, mode, self
                )
                self._log_session_details(result.session_id)
            except Exception as e:
                logger.error(f"RunSpace session failed: {e}", exc_info=True)
                raise RuntimeError(f"Optimization failed: {str(e)}")

            if mode == "container":
                import_dir = (
                    session_workspace(result.session_id) / "agent_workspace" / "editable"
                )
            else:
                import_dir = skill_dir

            clean_dir = temp_path / "import_clean"
            shutil.copytree(str(import_dir), str(clean_dir))
            req_file = clean_dir / REQUIRED_OUTPUTS_FILENAME
            opt_metadata: Dict[str, Any] = {}
            if req_file.exists():
                try:
                    opt_metadata = json.loads(req_file.read_text())
                    req_file.unlink()
                except Exception as e:
                    logger.warning(f"Could not parse {REQUIRED_OUTPUTS_FILENAME}: {e}")
            else:
                logger.warning(f"{REQUIRED_OUTPUTS_FILENAME} not found in session output")

            final_name = self._generate_output_skill_name(original_name, override=output_skill_name)

            try:
                skill_name_result, skill_description, imported_tools, imported_snippets, ignored = (
                    import_from_anthropic_skill(
                        source_type="folder",
                        source_data=str(clean_dir),
                        snippet_mode="file",
                        treat_all_as_documents=False,
                    )
                )
                logger.info(
                    f"Imported '{skill_name_result}': {len(imported_tools)} tools, "
                    f"{len(imported_snippets)} snippets, {len(ignored)} ignored"
                )

                tool_uuids = []
                for tool in imported_tools:
                    try:
                        tool_tags = list(getattr(tool, "tags", None) or [])
                        tool_data = {
                            "name": tool.name,
                            "description": tool.description or "",
                            "programming_language": tool.programming_language or "python",
                            "params": tool.params or {},
                            "returns": tool.returns or {},
                            "tags": tool_tags,
                        }
                        module_bytes = tool.module_content.encode() if tool.module_content else b""
                        module_filename = tool.source_file_name or f"{tool.name}.py"
                        created = self.store.create_tool(
                            tool_data, module_content=module_bytes, module_filename=module_filename
                        )
                        tool_uuids.append(created["uuid"])
                    except Exception as e:
                        logger.error(f"Failed to create tool '{tool.name}': {e}", exc_info=True)

                snippet_uuids = []
                for snippet in imported_snippets:
                    try:
                        snippet_tags = list(getattr(snippet, "tags", None) or [])
                        snippet_data = {
                            "name": snippet.name,
                            "content": snippet.content,
                            "tags": snippet_tags,
                            "description": snippet.description or "",
                            "version": getattr(snippet, "version", "1.0.0"),
                        }
                        created = self.store.create_snippet(snippet_data)
                        snippet_uuids.append(created["uuid"])
                    except Exception as e:
                        logger.error(f"Failed to create snippet '{snippet.name}': {e}", exc_info=True)

                inherited_tags = [t for t in skill.get("tags", []) if t]
                skill_data = {
                    "name": final_name,
                    "description": skill_description,
                    "tool_uuids": tool_uuids,
                    "snippet_uuids": snippet_uuids,
                    "tags": list({"optimized"} | set(inherited_tags)),
                }
                created_skill = self.store.create_skill(skill_data)
                logger.info(f"Created optimized skill '{final_name}' ({created_skill['uuid']})")

                self.store.update_skill_metadata(
                    created_skill["uuid"],
                    {
                        "optimization": {
                            **opt_metadata,
                            "source_skill_uuid": skill_uuid,
                            "source_skill_name": original_name,
                        }
                    },
                )

                return {
                    "success": True,
                    "skill": created_skill,
                    "tools_count": len(tool_uuids),
                    "snippets_count": len(snippet_uuids),
                    "optimization_rationale": opt_metadata.get("optimization_rationale", ""),
                }

            except Exception as e:
                logger.error(f"Failed to import optimized skill: {e}", exc_info=True)
                raise RuntimeError(f"Skill import failed: {str(e)}")

    def get_router(self):
        """Register plugin API routes."""
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel
        from typing import List, Optional

        router = APIRouter()

        class OptimizeSkillRequest(BaseModel):
            skill_uuid: str
            output_skill_name: Optional[str] = None
            include_metadata: bool = True
            trajectories_dir: Optional[str] = None
            additional_context_dir: Optional[str] = None
            agent_env: Optional[Dict[str, str]] = None
            execution_mode: Optional[str] = None
            max_turns: Optional[int] = None

        @router.post("/optimize-skill")
        async def optimize_skill_endpoint(request: OptimizeSkillRequest):
            """Optimize an existing skill using RunSpace."""
            if not self.is_enabled():
                raise HTTPException(status_code=503, detail=self._status_message)

            try:
                result = await self.optimize_skill(
                    skill_uuid=request.skill_uuid,
                    output_skill_name=request.output_skill_name,
                    include_metadata=request.include_metadata,
                    trajectories_dir=request.trajectories_dir,
                    additional_context_dir=request.additional_context_dir,
                    agent_env=request.agent_env,
                    execution_mode=request.execution_mode,
                    max_turns=request.max_turns,
                )
                return {
                    "success": True,
                    "message": f"Skill '{result['skill']['name']}' optimized successfully.",
                    "skill_name": result["skill"]["name"],
                    "skill_uuid": result["skill"]["uuid"],
                    "tools_count": result["tools_count"],
                    "snippets_count": result["snippets_count"],
                    "optimization_rationale": result.get("optimization_rationale", ""),
                }
            except ValueError as e:
                status = 404 if "not found" in str(e) else 400
                raise HTTPException(status_code=status, detail=str(e))
            except Exception as e:
                logger.error(f"Optimization endpoint error: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))

        return router

    def get_cli_commands(self) -> Optional[Dict[str, Any]]:
        return None

    def get_ui_config(self) -> Optional[Dict[str, Any]]:
        return {
            "icon": "SparklesIcon",
            "color": "#F59E0B",
            "actions": [
                {
                    "label": "Optimize Skill",
                    "endpoint": "/api/plugins/skill-optimizer/optimize-skill",
                    "method": "POST",
                    "params_schema": {
                        "type": "object",
                        "properties": {
                            "skill_uuid": {
                                "type": "string",
                                "description": "UUID of the skill to optimize",
                            },
                            "output_skill_name": {
                                "type": "string",
                                "description": "Name for the optimized skill (auto-generated if not set)",
                            },
                            "include_metadata": {
                                "type": "boolean",
                                "default": True,
                                "description": "Include skill tags and extra metadata in context",
                            },
                            "trajectories_dir": {
                                "type": "string",
                                "description": "Local path to folder containing execution trajectories",
                            },
                            "additional_context_dir": {
                                "type": "string",
                                "description": "Local path to folder with additional optimization context",
                            },
                            "agent_env": {
                                "type": "object",
                                "description": "Credential overrides for Claude Code (e.g., ANTHROPIC_API_KEY)",
                            },
                            "execution_mode": {
                                "type": "string",
                                "enum": ["container", "local"],
                                "default": "container",
                                "description": "Execution mode: 'local' (faster) or 'container' (safer, requires Docker)",
                            },
                            "max_turns": {
                                "type": "integer",
                                "description": "Maximum conversation turns for Claude Code (default: 300)",
                            },
                        },
                        "required": ["skill_uuid"],
                    },
                }
            ],
        }

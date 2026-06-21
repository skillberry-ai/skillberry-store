"""
Skillberry Plugin Anthropic Skill Generator - generates Anthropic skills from descriptions.
Uses runspace-agent to create skills and imports them into the store.
"""

import asyncio
import json
import logging
import os
import tempfile
import threading
import time
import uuid
from typing import Dict, Any, Literal, Optional
from pathlib import Path

from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType
from skillberry_store.plugins.claude_credentials import (
    load_claude_settings,
    settings_env,
    has_api_access,
    build_agent_env,
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


async def create_skill(prompt, skill_dir, context_dir, options, mode, plugin_instance):
    """Create and execute a runspace-agent session to generate a skill.

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

    logger.info(
        f"Running agent in {mode} mode (session {gen_session_id})"
        + (" — container will stream logs below..." if mode == "container"
           else " — watching workspace for progress...")
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


class SkillberryPluginAnthropicSkillGenerator(PluginBase):
    """Plugin for generating Anthropic skills from descriptions using runspace-agent."""

    def __init__(self):
        super().__init__()
        
        self._metadata = PluginMetadata(
            name="Anthropic Skill Generator",
            version="0.1.0",
            description="Generate Anthropic skills from descriptions using runspace-agent",
            plugin_type=PluginType.CREATOR,
        )
        
        self._status_message = "Initializing..."
        self._runspace_available = False
        self._credentials_configured = False
        self._execution_mode = os.getenv("RUNSPACE_MODE", "container")  # Default to container for safety
        self._claude_settings = None
        
        # Try to load Claude settings from ~/.claude/settings.json
        self._load_claude_settings()
        
        # Check if runspace-agent is available (module-level import)
        if runspace_agent is not None:
            try:
                self._runspace_available = True
                logger.info("runspace-agent library available")

                # Check for Anthropic credentials (env vars or settings file)
                self._credentials_configured = self._check_credentials()

                if self._credentials_configured:
                    mode_label = f" ({self._execution_mode} mode)" if self._execution_mode else ""
                    source = " from ~/.claude/settings.json" if self._claude_settings else ""
                    self._status_message = f"Ready{mode_label}{source}"
                    logger.info(f"Plugin ready with {self._execution_mode} execution mode")
                else:
                    self._status_message = "Missing credentials: Set ANTHROPIC_API_KEY, configure ~/.claude/settings.json, or provide ANTHROPIC_BASE_URL + ANTHROPIC_AUTH_TOKEN"
                    logger.warning("Anthropic credentials not configured")

            except Exception as e:
                self._status_message = f"Configuration error: {str(e)}"
                logger.error(f"Failed to initialize runspace-agent: {e}", exc_info=True)
        else:
            self._status_message = "Missing dependency: runspace-agent not installed"
            logger.warning("runspace-agent not installed, plugin will be disabled")
    
    def _load_claude_settings(self):
        self._claude_settings = load_claude_settings()

    @staticmethod
    def _has_api_access(source) -> bool:
        return has_api_access(source)

    def _claude_settings_env(self):
        return settings_env(self._claude_settings)

    def _check_credentials(self) -> bool:
        return self._has_api_access(os.environ) or self._has_api_access(self._claude_settings_env())

    def _build_claude_env(self, override_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        return build_agent_env(self._claude_settings, override_env)

    @property
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return self._metadata
    
    def get_status_message(self) -> str:
        """Return current plugin status."""
        return self._status_message

    def is_enabled(self) -> bool:
        """Plugin is enabled if runspace-agent is available and credentials are configured."""
        return self._runspace_available and self._credentials_configured

    def _stream_docker_logs(self, workspace_root: Path, stop: threading.Event) -> None:
        """Background thread: find the container mounting workspace_root and tail its logs."""
        try:
            import docker  # type: ignore[import-untyped]
            client = docker.from_env()
            container = None
            # Wait up to 30 s for the container to appear
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
                logger.debug("Docker log streaming: container not found within timeout")
                return

            cid = container.short_id
            logger.info(f"  [container:{cid}] Attaching to container logs...")
            for chunk in container.logs(stream=True, follow=True, stderr=True, stdout=True):
                if stop.is_set():
                    break
                line = chunk.decode("utf-8", errors="replace").rstrip()
                if line:
                    logger.info(f"  [container:{cid}] {line}")

        except ImportError:
            logger.debug("Docker SDK not available — install runspace-agent[container] for live logs")
        except Exception as e:
            logger.debug(f"Docker log streaming ended: {e}")

    async def _stream_progress(
        self,
        mode: str,
        workspace_root: Path,
        run_task: "asyncio.Task[Any]",
    ) -> None:
        """Poll workspace for new files while agent runs; also stream Docker logs in container mode."""
        editable = workspace_root / "agent_workspace" / "editable"
        seen: set = set()

        stop = threading.Event()
        if mode == "container":
            t = threading.Thread(
                target=self._stream_docker_logs,
                args=(workspace_root, stop),
                daemon=True,
            )
            t.start()

        try:
            while not run_task.done():
                await asyncio.sleep(5)
                if not editable.exists():
                    continue
                current = {str(p) for p in editable.rglob("*") if p.is_file()}
                for f in sorted(current - seen):
                    rel = Path(f).relative_to(editable)
                    logger.info(f"  [progress] created: {rel}")
                seen = current
        finally:
            stop.set()

    def _log_session_details(self, session_id: str) -> None:
        """Log the summary and key conversation milestones from a completed session."""
        try:
            from runspace_agent.workspaces import session_workspace
            workspace = session_workspace(session_id)

            # Log human-readable summary if available
            summary_path = workspace / "summary.md"
            if summary_path.exists():
                summary = summary_path.read_text(encoding="utf-8").strip()
                logger.info(f"Session summary:\n{summary}")

            # Parse conversation.json for key milestones
            conv_path = workspace / "conversation.json"
            if not conv_path.exists():
                return

            conv = json.loads(conv_path.read_text(encoding="utf-8"))
            if not isinstance(conv, list):
                return

            logger.info(f"Agent conversation replay ({len(conv)} messages):")
            for msg in conv:
                t = msg.get("type", "")
                data = msg.get("data", msg)

                if t == "assistant":
                    for block in (data.get("content") or []):
                        if not isinstance(block, dict):
                            continue
                        if block.get("type") == "text":
                            text = block["text"].strip().replace("\n", " ")
                            if text:
                                logger.info(f"  [agent] {text[:200]}")
                        elif block.get("type") == "tool_use":
                            inp = block.get("input", {})
                            detail = (
                                inp.get("command")
                                or inp.get("file_path")
                                or inp.get("path")
                                or str(inp)[:80]
                            )
                            logger.info(f"  [tool]  {block['name']}: {str(detail)[:120]}")

                elif t == "result":
                    turns = data.get("num_turns", "?")
                    cost = data.get("total_cost_usd")
                    usage = data.get("usage", {})
                    out_tok = usage.get("output_tokens", "?")
                    cache_r = usage.get("cache_read_input_tokens", 0)
                    cost_str = f" ${cost:.4f}" if cost is not None else ""
                    logger.info(
                        f"  [done]  {turns} turns, {out_tok} output tokens"
                        f", {cache_r} cache-read tokens{cost_str}"
                    )

        except Exception as e:
            logger.debug(f"Could not read session details for {session_id}: {e}")

    async def generate_skill(
        self,
        description: str,
        skill_name: Optional[str] = None,
        tags: Optional[list] = None,
        agent_env: Optional[Dict[str, str]] = None,
        execution_mode: Optional[str] = None,
        max_turns: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate an Anthropic skill from a description using runspace-agent.
        
        Args:
            description: Natural language description of the skill to create
            skill_name: Optional name for the skill
            tags: Optional list of tags to apply to the imported skill
            agent_env: Optional environment variables for Claude Code (API keys, etc.)
            execution_mode: Optional execution mode ("local" or "container")
            max_turns: Optional maximum conversation turns for Claude Code
            
        Returns:
            Dict with skill details (uuid, name, tools, etc.)
        """
        if not self._runspace_available:
            raise RuntimeError("runspace-agent not available")

        if self._store_api is None:
            raise RuntimeError("Store API not available")

        if not self._credentials_configured and not agent_env:
            raise RuntimeError(
                "Anthropic credentials not configured. Set ANTHROPIC_API_KEY or provide agent_env"
            )

        logger.info(f"Generating Anthropic skill from description: {description[:100]}...")

        from claude_code_sdk import ClaudeCodeOptions

        # Build environment for Claude Code
        claude_env = self._build_claude_env(agent_env)

        # Configure Claude Code options.
        # Use agent_options (not a pre-built agent) so both local and container
        # modes can read the env vars from the session — container mode reads
        # session.agent_options.env to inject credentials into the Docker container.
        options = ClaudeCodeOptions(
            env=claude_env,
            max_turns=max_turns or int(os.getenv("RUNSPACE_MAX_TURNS", "300")),
        )
        
        # Determine execution mode
        raw_mode = execution_mode or self._execution_mode
        mode: Literal["local", "container"] = "container" if raw_mode == "container" else "local"
        
        # Create a temporary directory for the generated skill
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            skill_dir = temp_path / "generated_skill"
            skill_dir.mkdir(exist_ok=True)
            context_dir = temp_path / "context"
            context_dir.mkdir(exist_ok=True)
            
            logger.info(f"Creating skill in temporary directory: {skill_dir}")
            
            # Create a prompt for skill generation
            prompt = f"""Create a new Anthropic skill based on this description:

{description}

Generate a complete skill with:
1. A SKILL.md file with proper frontmatter (name, description)
2. Any necessary tool implementations
3. Documentation and examples
4. Follow Anthropic skill best practices

The skill should be production-ready and well-documented."""

            if skill_name:
                prompt += f"\n\nUse '{skill_name}' as the skill name."
            
            # Generate the skill using runspace-agent
            try:
                result = await create_skill(prompt, skill_dir, context_dir, options, mode, self)
                self._log_session_details(result.session_id)

            except Exception as e:
                logger.error(f"Failed to generate skill with runspace-agent: {e}", exc_info=True)
                raise RuntimeError(f"Skill generation failed: {str(e)}")
            
            # Import the generated skill into the store using the Anthropic importer
            try:
                # Container mode does not sync files back to session.editable_dir —
                # generated files live in the runspace session workspace instead.
                # Local mode does sync back, so skill_dir is correct there.
                if mode == "container":
                    import_dir = session_workspace(result.session_id) / "agent_workspace" / "editable"
                else:
                    import_dir = skill_dir

                logger.info(f"Importing generated skill from {import_dir}...")

                # Import from the folder
                skill_name_result, skill_description, tools, snippets, ignored_files = (
                    import_from_anthropic_skill(
                        source_type="folder",
                        source_data=str(import_dir),
                        snippet_mode="file",
                        treat_all_as_documents=False
                    )
                )
                
                logger.info(
                    f"Imported skill '{skill_name_result}': "
                    f"{len(tools)} tools, {len(snippets)} snippets, "
                    f"{len(ignored_files)} ignored files"
                )
                
                # Create tools in the store
                tool_uuids = []
                for tool in tools:
                    try:
                        tool_tags = list(getattr(tool, "tags", None) or [])
                        if tags:
                            tool_tags.extend(t for t in tags if t not in tool_tags)
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
                        created_tool = self.store.create_tool(
                            tool_data,
                            module_content=module_bytes,
                            module_filename=module_filename,
                        )
                        tool_uuids.append(created_tool["uuid"])
                        logger.info(f"Created tool: {tool.name} ({created_tool['uuid']})")
                        
                    except Exception as e:
                        logger.error(f"Failed to create tool {tool.name}: {e}", exc_info=True)
                
                # Create snippets in the store
                snippet_uuids = []
                for snippet in snippets:
                    try:
                        snippet_tags = list(getattr(snippet, "tags", None) or [])
                        if tags:
                            snippet_tags.extend(t for t in tags if t not in snippet_tags)
                        snippet_data = {
                            "name": snippet.name,
                            "content": snippet.content,
                            "tags": snippet_tags,
                            "description": snippet.description or "",
                            "version": getattr(snippet, "version", "1.0.0"),
                        }
                        
                        created_snippet = self.store.create_snippet(snippet_data)
                        snippet_uuids.append(created_snippet["uuid"])
                        logger.info(f"Created snippet: {snippet.name} ({created_snippet['uuid']})")
                        
                    except Exception as e:
                        logger.error(f"Failed to create snippet {snippet.name}: {e}", exc_info=True)
                
                # Create the skill in the store
                final_skill_name = skill_name or skill_name_result
                skill_tags = ["anthropic", "generated"]
                if tags:
                    skill_tags.extend(tags)
                
                skill_data = {
                    "name": final_skill_name,
                    "description": skill_description,
                    "tool_uuids": tool_uuids,
                    "tags": skill_tags,
                }
                
                created_skill = self.store.create_skill(skill_data)
                logger.info(f"Skill created with UUID: {created_skill.get('uuid')}")
                
                return {
                    "success": True,
                    "skill": created_skill,
                    "tools_count": len(tool_uuids),
                    "snippets_count": len(snippet_uuids),
                    "ignored_files": ignored_files,
                }
                
            except Exception as e:
                logger.error(f"Failed to import generated skill: {e}", exc_info=True)
                raise RuntimeError(f"Skill import failed: {str(e)}")

    def get_router(self):
        """Register plugin routes."""
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel
        from typing import List, Optional
        
        router = APIRouter()
        
        class GenerateSkillRequest(BaseModel):
            description: str
            skill_name: Optional[str] = None
            tags: Optional[List[str]] = None
            agent_env: Optional[Dict[str, str]] = None
            execution_mode: Optional[str] = None
            max_turns: Optional[int] = None
        
        @router.post("/generate-skill")
        async def generate_skill_endpoint(request: GenerateSkillRequest):
            """Generate an Anthropic skill from a description."""
            if not self.is_enabled():
                raise HTTPException(status_code=503, detail=self._status_message)
            
            try:
                result = await self.generate_skill(
                    description=request.description,
                    skill_name=request.skill_name,
                    tags=request.tags,
                    agent_env=request.agent_env,
                    execution_mode=request.execution_mode,
                    max_turns=request.max_turns
                )
                return {
                    "success": True,
                    "message": f"Skill '{result['skill']['name']}' generated successfully.",
                    "skill_name": result["skill"]["name"],
                    "skill_uuid": result["skill"]["uuid"],
                    "tools_count": result["tools_count"],
                    "snippets_count": result["snippets_count"],
                }
            except Exception as e:
                logger.error(f"Failed to generate skill: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
        
        return router
    
    def get_cli_commands(self) -> Optional[Dict[str, Any]]:
        """No CLI commands for this plugin."""
        return None
    
    def get_ui_config(self) -> Optional[Dict[str, Any]]:
        """Return UI configuration for the plugin."""
        return {
            "icon": "WandIcon",
            "color": "#8B5CF6",
            "actions": [
                {
                    "label": "Generate Anthropic Skill",
                    "endpoint": "/api/plugins/anthropic-skill-generator/generate-skill",
                    "method": "POST",
                    "params_schema": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "Description of the Anthropic skill to generate"
                            },
                            "skill_name": {
                                "type": "string",
                                "description": "Optional name for the skill"
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional tags to apply to the skill"
                            },
                            "agent_env": {
                                "type": "object",
                                "title": "Environment overrides (optional)",
                                "description": (
                                    "Per-run overrides for the Claude Code agent environment. "
                                    "Your ~/.claude/settings.json env block and the server's "
                                    "ANTHROPIC_*/CLAUDE_* variables are already loaded automatically; "
                                    "only set this to override them."
                                )
                            },
                            "execution_mode": {
                                "type": "string",
                                "enum": ["container", "local"],
                                "default": "container",
                                "description": "Execution mode: 'local' (faster) or 'container' (safer, requires Docker)"
                            },
                            "max_turns": {
                                "type": "integer",
                                "description": "Maximum conversation turns for Claude Code (default: 300)"
                            }
                        },
                        "required": ["description"]
                    }
                }
            ]
        }

# Made with Bob

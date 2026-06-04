"""
Skillberry Plugin Security - LLM-based security evaluation plugin.
Uses llm-switchboard for LLM integration.
"""

import os
import logging
import json
from typing import Dict, Any, Optional, List

from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType

logger = logging.getLogger(__name__)


class SkillberryPluginSecurity(PluginBase):
    """Plugin for evaluating skills, tools, and snippets for security posture using LLM."""

    def __init__(self):
        super().__init__()

        self._metadata = PluginMetadata(
            name="Security Evaluator",
            version="0.1.0",
            description="Evaluate content security posture using LLM",
            plugin_type=PluginType.EVALUATOR,
        )

        self.llm_client = None
        self._status_message = "Initializing..."

        try:
            from llm_switchboard import get_llm

            provider_name = os.getenv("LLM_PROVIDER", "openai.async")
            model_name = os.getenv("LLM_MODEL", "gpt-4")

            logger.info(f"Initializing LLM: provider={provider_name}, model={model_name}")

            LLMClientClass = get_llm(provider_name)
            self.llm_client = LLMClientClass(model_name=model_name)
            self._status_message = f"Ready (using {provider_name})"

            logger.info("LLM client initialized successfully")

        except ImportError:
            self._status_message = "Missing dependency: llm-switchboard not installed"
            logger.warning("llm-switchboard not installed, plugin will be disabled")
        except Exception as e:
            self._status_message = f"Configuration error: {str(e)}"
            logger.error(f"Failed to initialize LLM client: {e}", exc_info=True)

        self._register_event_handlers()

    def _register_event_handlers(self) -> None:
        pass  # implemented in Task 7

    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata

    def get_status_message(self) -> str:
        return self._status_message

    def is_enabled(self) -> bool:
        return self.llm_client is not None

    def _strip_score_tags(self, tags: List[str]) -> List[str]:
        return [t for t in tags if not t.startswith("security-score:")]

    def _build_context(self, obj: Dict[str, Any], content_type: str) -> str:
        """Build rich context string for the LLM security evaluation prompt."""
        lines = [
            f"Name: {obj.get('name', 'N/A')}",
            f"Description: {obj.get('description', 'N/A')}",
        ]

        if obj.get("version"):
            lines.append(f"Version: {obj['version']}")
        if obj.get("state"):
            lines.append(f"State: {obj['state']}")
        if obj.get("tags"):
            lines.append(f"Tags: {', '.join(obj['tags'])}")

        extra = obj.get("extra")
        if extra and isinstance(extra, dict):
            # Exclude previous evaluation results so they don't bias the new evaluation.
            extra_for_context = {k: v for k, v in extra.items() if k != "evaluation"}
            if extra_for_context:
                lines.append(f"Extra info: {json.dumps(extra_for_context)}")

        if content_type == "tool":
            if obj.get("programming_language"):
                lines.append(f"Language: {obj['programming_language']}")
            if obj.get("packaging_format"):
                lines.append(f"Packaging format: {obj['packaging_format']}")
            if obj.get("packaging_params"):
                lines.append(f"Packaging params: {json.dumps(obj['packaging_params'])}")
            if obj.get("params"):
                lines.append(f"Parameters: {json.dumps(obj['params'])}")
            if obj.get("returns"):
                lines.append(f"Returns: {json.dumps(obj['returns'])}")
            if obj.get("dependencies"):
                lines.append(f"Dependencies: {', '.join(obj['dependencies'])}")

            module_name = obj.get("module_name")
            if module_name and self._store_api is not None:
                try:
                    code = self.store.tools.read_file(
                        obj["uuid"], module_name, raw_content=True
                    )
                    lines.append(f"\nCode ({module_name}):\n```\n{code}\n```")
                except Exception as e:
                    logger.info(f"Could not read code for tool {obj.get('uuid')}: {e}")

        elif content_type == "skill":
            tool_uuids = obj.get("tool_uuids") or []
            snippet_uuids = obj.get("snippet_uuids") or []
            lines.append(
                f"Contains {len(tool_uuids)} tool(s): "
                f"{', '.join(tool_uuids) if tool_uuids else 'none'}"
            )
            lines.append(
                f"Contains {len(snippet_uuids)} snippet(s): "
                f"{', '.join(snippet_uuids) if snippet_uuids else 'none'}"
            )

        elif content_type == "snippet":
            if obj.get("content_type"):
                lines.append(f"Content type: {obj['content_type']}")
            if obj.get("content"):
                lines.append(f"\nContent:\n```\n{obj['content']}\n```")

        return "\n".join(lines)

    async def _write_security_to_store(
        self,
        uuid: str,
        content_type: str,
        obj: Dict[str, Any],
        evaluation: Dict[str, Any],
    ) -> None:
        pass  # implemented in Task 4

    async def evaluate_security(self, uuid: str, content_type: str) -> Dict[str, Any]:
        raise NotImplementedError  # implemented in Task 5

    def get_router(self):
        return None  # implemented in Task 6

    def get_cli_commands(self) -> Optional[Dict[str, Any]]:
        return None

    def get_ui_config(self) -> Optional[Dict[str, Any]]:
        return None  # implemented in Task 6

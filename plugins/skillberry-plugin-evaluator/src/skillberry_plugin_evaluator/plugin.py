"""
Skillberry Plugin Evaluator - LLM-based quality/performance evaluation plugin.
Uses llm-switchboard for LLM integration.
"""

import os
import logging
import json
from typing import Dict, Any, Optional, List

from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType

logger = logging.getLogger(__name__)


class SkillberryPluginEvaluator(PluginBase):
    """Plugin for evaluating skills, tools, and snippets using LLM."""

    def __init__(self):
        super().__init__()

        self._metadata = PluginMetadata(
            name="Content Evaluator",
            version="0.1.0",
            description="Evaluate content quality and performance using LLM",
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
        """Register on_content_added handlers for automatic evaluation on object creation."""
        from skillberry_store.plugins.events import _event_handlers

        for content_type in ("tool", "skill", "snippet"):
            async def _handle_added(uuid: str, ct=content_type):
                if not self.is_enabled() or self._store_api is None:
                    return
                try:
                    await self.evaluate_object(uuid, ct)
                except Exception as e:
                    logger.error(
                        f"Auto-evaluation failed for {ct} {uuid}: {e}", exc_info=True
                    )
                # For skills, also evaluate referenced tools and snippets.
                # Import flows (e.g. import-anthropic-skill) write tools/snippets
                # directly to the handler without emitting per-object events, so
                # those objects would otherwise never be evaluated.
                if ct == "skill":
                    try:
                        skill_obj = self.store.get_skill(uuid)
                    except Exception:
                        skill_obj = None
                    if skill_obj:
                        for tool_uuid in skill_obj.get("tool_uuids") or []:
                            try:
                                await self.evaluate_object(tool_uuid, "tool")
                            except Exception as e:
                                logger.error(
                                    f"Auto-evaluation failed for tool {tool_uuid}: {e}",
                                    exc_info=True,
                                )
                        for snippet_uuid in skill_obj.get("snippet_uuids") or []:
                            try:
                                await self.evaluate_object(snippet_uuid, "snippet")
                            except Exception as e:
                                logger.error(
                                    f"Auto-evaluation failed for snippet {snippet_uuid}: {e}",
                                    exc_info=True,
                                )

            event_name = f"content_added:{content_type}"
            if event_name not in _event_handlers:
                _event_handlers[event_name] = []
            _event_handlers[event_name].append(_handle_added)

    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata

    def get_status_message(self) -> str:
        return self._status_message

    def is_enabled(self) -> bool:
        return self.llm_client is not None

    def _build_context(self, obj: Dict[str, Any], content_type: str) -> str:
        """Build rich context string for the LLM evaluation prompt."""
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

    def _strip_score_tags(self, tags: List[str]) -> List[str]:
        """Remove evaluator score tags so re-evaluation is a clean overwrite."""
        score_prefixes = ("quality-score:", "performance-score:")
        return [t for t in tags if not any(t.startswith(p) for p in score_prefixes)]

    async def _write_evaluation_to_store(
        self,
        uuid: str,
        content_type: str,
        obj: Dict[str, Any],
        evaluation: Dict[str, Any],
    ) -> None:
        """Write score tags and textual evaluations back to the store object."""
        score_tags = [
            f"quality-score:{evaluation['quality_score']}",
            f"performance-score:{evaluation['performance_score']}",
        ]

        existing_tags = self._strip_score_tags(obj.get("tags") or [])
        obj["tags"] = existing_tags + score_tags

        if not isinstance(obj.get("extra"), dict):
            obj["extra"] = {}
        obj["extra"]["evaluation"] = {
            "quality": {
                "score": evaluation["quality_score"],
                "evaluation": evaluation["quality_evaluation"],
            },
            "performance": {
                "score": evaluation["performance_score"],
                "evaluation": evaluation["performance_evaluation"],
            },
        }

        if content_type == "tool":
            self.store.update_tool(uuid, obj)
        elif content_type == "skill":
            self.store.update_skill(uuid, obj)
        elif content_type == "snippet":
            self.store.update_snippet(uuid, obj)

    async def evaluate_object(self, uuid: str, content_type: str) -> Dict[str, Any]:
        """
        Evaluate a store object on quality and performance.

        Fetches the full object from the store, sends it to the LLM, then
        stores scores as tags (quality-score:N etc.) and textual evaluations
        in extra["evaluation"].

        Args:
            uuid: UUID of the object to evaluate
            content_type: "tool", "skill", or "snippet"

        Returns:
            Dict with quality_score, performance_score (int 1-10)
            and quality_evaluation, performance_evaluation (str)
        """
        if not self.llm_client:
            raise RuntimeError("LLM client not initialized")
        if self._store_api is None:
            raise RuntimeError("Store API not available")

        if content_type == "tool":
            obj = self.store.get_tool(uuid)
        elif content_type == "skill":
            obj = self.store.get_skill(uuid)
        elif content_type == "snippet":
            obj = self.store.get_snippet(uuid)
        else:
            raise ValueError(f"Unknown content_type: {content_type}")

        if not obj:
            raise ValueError(f"{content_type.capitalize()} {uuid} not found in store")

        logger.info(f"Evaluating {content_type} {uuid}: {obj.get('name', 'unnamed')}")

        context = self._build_context(obj, content_type)

        prompt = f"""You are evaluating a {content_type} from a skills store.

{context}

Evaluate this {content_type} on two dimensions and return a JSON object with exactly these four fields:
- quality_score: integer 1-10 (clarity, structure, completeness, best practices)
- quality_evaluation: string (one paragraph)
- performance_score: integer 1-10 (efficiency, resource usage, scalability)
- performance_evaluation: string (one paragraph)

Return ONLY the JSON object, no other text."""

        logger.debug(f"Calling LLM for {content_type} {uuid}")
        response = await self.llm_client.generate_async(prompt=prompt)
        logger.info(f"Received LLM response ({len(response)} chars)")

        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start < 0 or end <= start:
                raise ValueError("No JSON object found in LLM response")
            evaluation = json.loads(response[start:end])

            required_fields = [
                "quality_score", "quality_evaluation",
                "performance_score", "performance_evaluation",
            ]
            for field in required_fields:
                if field not in evaluation:
                    raise ValueError(f"Missing field in LLM response: {field}")

            for score_field in ("quality_score", "performance_score"):
                evaluation[score_field] = int(evaluation[score_field])

        except Exception as e:
            logger.warning(f"Failed to parse LLM evaluation response: {e}")
            raise RuntimeError(f"Failed to parse LLM response: {str(e)}")

        await self._write_evaluation_to_store(uuid, content_type, obj, evaluation)
        logger.info(
            f"Evaluation stored for {content_type} {uuid}: "
            f"quality={evaluation['quality_score']}, "
            f"performance={evaluation['performance_score']}"
        )

        return evaluation

    def get_router(self):
        """Register plugin routes."""
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel

        router = APIRouter()

        class EvaluateRequest(BaseModel):
            uuid: str
            content_type: str  # "tool", "skill", or "snippet"

        @router.post("/evaluate")
        async def evaluate_endpoint(request: EvaluateRequest):
            """Evaluate a store object and store quality/performance scores."""
            if not self.is_enabled():
                raise HTTPException(status_code=503, detail=self._status_message)

            if request.content_type not in ("tool", "skill", "snippet"):
                raise HTTPException(
                    status_code=400,
                    detail="content_type must be 'tool', 'skill', or 'snippet'",
                )

            try:
                result = await self.evaluate_object(
                    uuid=request.uuid,
                    content_type=request.content_type,
                )
                return {"success": True, "uuid": request.uuid, **result}
            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                logger.error(
                    f"Failed to evaluate {request.content_type} {request.uuid}: {e}",
                    exc_info=True,
                )
                raise HTTPException(status_code=500, detail=str(e))

        return router

    def get_cli_commands(self) -> Optional[Dict[str, Any]]:
        return None

    def get_ui_config(self) -> Optional[Dict[str, Any]]:
        return {
            "icon": "CheckCircleIcon",
            "color": "#28A745",
            "actions": [
                {
                    "label": "Evaluate",
                    "endpoint": "/api/plugins/evaluator/evaluate",
                    "method": "POST",
                    "params_schema": {
                        "type": "object",
                        "properties": {
                            "uuid": {
                                "type": "string",
                                "description": "UUID of the object to evaluate",
                            },
                            "content_type": {
                                "type": "string",
                                "enum": ["tool", "skill", "snippet"],
                                "description": "Type of object to evaluate",
                            },
                        },
                        "required": ["uuid", "content_type"],
                    },
                }
            ],
        }

# Made with Bob

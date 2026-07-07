"""
Skillberry Plugin Evaluator - LLM-based quality/performance evaluation plugin.

Out-of-process SDK version. Uses llm-switchboard for LLM integration.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from skillberry_plugin_sdk import PluginLifecycleBase, on_event

logger = logging.getLogger(__name__)


class SkillberryPluginEvaluator(PluginLifecycleBase):
    """Plugin for evaluating skills, tools, and snippets using LLM."""

    manifest_path = "manifest.yaml"

    def __init__(self, manifest=None):
        super().__init__(manifest=manifest)
        self.llm_client = None
        self._status_message = "Initializing..."

    # Lifecycle ---------------------------------------------------------------

    async def on_start(self) -> None:
        """Initialize the LLM client from env-driven configuration."""
        try:
            from llm_switchboard import get_llm

            provider_name = os.getenv("LLM_PROVIDER", "openai.async")
            model_name = os.getenv("LLM_MODEL", "gpt-4")

            logger.info(
                "Initializing LLM: provider=%s, model=%s", provider_name, model_name
            )

            LLMClientClass = get_llm(provider_name)
            self.llm_client = LLMClientClass(model_name=model_name)
            self._status_message = f"Ready (using {provider_name})"

            logger.info("LLM client initialized successfully")
        except ImportError:
            self._status_message = "Missing dependency: llm-switchboard not installed"
            logger.warning("llm-switchboard not installed, plugin will be disabled")
        except Exception as e:
            self._status_message = f"Configuration error: {str(e)}"
            logger.error("Failed to initialize LLM client: %s", e, exc_info=True)

    async def is_ready(self) -> Dict[str, Any]:
        ready = self.llm_client is not None
        return {
            "ready": ready,
            "missing_config": [] if ready else ["llm_client"],
        }

    def is_enabled(self) -> bool:
        return self.llm_client is not None

    def get_status_message(self) -> str:
        return self._status_message

    # Event handlers ---------------------------------------------------------

    @on_event("content.tool.added")
    async def on_tool_added(self, event) -> None:
        uuid = event.data.get("uuid") if isinstance(event.data, dict) else None
        if not uuid:
            return
        if not self.is_enabled():
            return
        try:
            await self.evaluate_object(uuid, "tool")
        except Exception as e:
            logger.error("Auto-evaluation failed for tool %s: %s", uuid, e, exc_info=True)

    @on_event("content.snippet.added")
    async def on_snippet_added(self, event) -> None:
        uuid = event.data.get("uuid") if isinstance(event.data, dict) else None
        if not uuid:
            return
        if not self.is_enabled():
            return
        try:
            await self.evaluate_object(uuid, "snippet")
        except Exception as e:
            logger.error(
                "Auto-evaluation failed for snippet %s: %s", uuid, e, exc_info=True
            )

    @on_event("content.skill.added")
    async def on_skill_added(self, event) -> None:
        uuid = event.data.get("uuid") if isinstance(event.data, dict) else None
        if not uuid:
            return
        if not self.is_enabled():
            return
        try:
            await self.evaluate_object(uuid, "skill")
        except Exception as e:
            logger.error(
                "Auto-evaluation failed for skill %s: %s", uuid, e, exc_info=True
            )

        # For skills, also evaluate referenced tools and snippets. Import flows
        # (e.g. import-anthropic-skill) write tools/snippets directly to the
        # handler without emitting per-object events, so those objects would
        # otherwise never be evaluated.
        try:
            skill_obj = await self.store.get_skill(uuid)
        except Exception:
            skill_obj = None
        if not skill_obj:
            return
        for tool_uuid in skill_obj.get("tool_uuids") or []:
            try:
                await self.evaluate_object(tool_uuid, "tool")
            except Exception as e:
                logger.error(
                    "Auto-evaluation failed for tool %s: %s",
                    tool_uuid,
                    e,
                    exc_info=True,
                )
        for snippet_uuid in skill_obj.get("snippet_uuids") or []:
            try:
                await self.evaluate_object(snippet_uuid, "snippet")
            except Exception as e:
                logger.error(
                    "Auto-evaluation failed for snippet %s: %s",
                    snippet_uuid,
                    e,
                    exc_info=True,
                )

    # Helpers ----------------------------------------------------------------

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
                lines.append(
                    f"Packaging params: {json.dumps(obj['packaging_params'])}"
                )
            if obj.get("params"):
                lines.append(f"Parameters: {json.dumps(obj['params'])}")
            if obj.get("returns"):
                lines.append(f"Returns: {json.dumps(obj['returns'])}")
            if obj.get("dependencies"):
                lines.append(f"Dependencies: {', '.join(obj['dependencies'])}")

            # NOTE: In the in-process plugin, we used to read the raw tool
            # source (self.store.tools.read_file(...)) and inline it in the
            # context. The out-of-process HTTP StoreClient does not expose
            # that handler access, so this code path is intentionally skipped.

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
            await self.store.update_tool(uuid, obj)
        elif content_type == "skill":
            await self.store.update_skill(uuid, obj)
        elif content_type == "snippet":
            await self.store.update_snippet(uuid, obj)

    async def evaluate_object(self, uuid: str, content_type: str) -> Dict[str, Any]:
        """
        Evaluate a store object on quality and performance.

        Fetches the full object from the store, sends it to the LLM, then
        stores scores as tags (quality-score:N etc.) and textual evaluations
        in extra["evaluation"].
        """
        if not self.llm_client:
            raise RuntimeError("LLM client not initialized")

        if content_type == "tool":
            obj = await self.store.get_tool(uuid)
        elif content_type == "skill":
            obj = await self.store.get_skill(uuid)
        elif content_type == "snippet":
            obj = await self.store.get_snippet(uuid)
        else:
            raise ValueError(f"Unknown content_type: {content_type}")

        if not obj:
            raise ValueError(f"{content_type.capitalize()} {uuid} not found in store")

        logger.info("Evaluating %s %s: %s", content_type, uuid, obj.get("name", "unnamed"))

        context = self._build_context(obj, content_type)

        prompt = f"""You are evaluating a {content_type} from a skills store.

{context}

Evaluate this {content_type} on two dimensions and return a JSON object with exactly these four fields:
- quality_score: integer 1-10 (clarity, structure, completeness, best practices)
- quality_evaluation: string (one paragraph)
- performance_score: integer 1-10 (efficiency, resource usage, scalability)
- performance_evaluation: string (one paragraph)

Return ONLY the JSON object, no other text."""

        logger.debug("Calling LLM for %s %s", content_type, uuid)
        response = await self.llm_client.generate_async(prompt=prompt)
        logger.info("Received LLM response (%d chars)", len(response))

        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start < 0 or end <= start:
                raise ValueError("No JSON object found in LLM response")
            evaluation = json.loads(response[start:end])

            required_fields = [
                "quality_score",
                "quality_evaluation",
                "performance_score",
                "performance_evaluation",
            ]
            for field in required_fields:
                if field not in evaluation:
                    raise ValueError(f"Missing field in LLM response: {field}")

            for score_field in ("quality_score", "performance_score"):
                evaluation[score_field] = int(evaluation[score_field])
        except Exception as e:
            logger.warning("Failed to parse LLM evaluation response: %s", e)
            raise RuntimeError(f"Failed to parse LLM response: {str(e)}")

        await self._write_evaluation_to_store(uuid, content_type, obj, evaluation)
        logger.info(
            "Evaluation stored for %s %s: quality=%s, performance=%s",
            content_type,
            uuid,
            evaluation["quality_score"],
            evaluation["performance_score"],
        )

        return evaluation

    # HTTP router ------------------------------------------------------------

    def get_router(self):
        """Register plugin routes."""
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel

        router = APIRouter(prefix=f"/plugins/{self.manifest.slug}", tags=["evaluator"])

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
                    "Failed to evaluate %s %s: %s",
                    request.content_type,
                    request.uuid,
                    e,
                    exc_info=True,
                )
                raise HTTPException(status_code=500, detail=str(e))

        return router


# Made with Bob

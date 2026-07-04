"""
Skillberry Plugin Security - LLM-based security evaluation plugin.

Out-of-process plugin using the skillberry-plugin-sdk. Uses llm-switchboard for
LLM integration.
"""

from __future__ import annotations

import os
import logging
import json
from typing import Any, Dict, List, Optional

from skillberry_plugin_sdk import PluginLifecycleBase, on_event

logger = logging.getLogger(__name__)


class SkillberryPluginSecurity(PluginLifecycleBase):
    """Plugin for evaluating skills, tools, and snippets for security posture using LLM."""

    manifest_path = "manifest.yaml"

    def __init__(self, manifest=None):
        super().__init__(manifest=manifest)
        self.llm_client = None
        self._status_message = "Initializing..."

    # ── lifecycle ────────────────────────────────────────────────────────────

    async def on_start(self) -> None:
        """Initialize the LLM client from env config."""
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

    async def is_ready(self) -> Dict[str, Any]:
        ready = self.llm_client is not None
        return {
            "ready": ready,
            "status": self._status_message,
            "missing_config": [] if ready else ["llm_client"],
        }

    def is_enabled(self) -> bool:
        return self.llm_client is not None

    # ── event handlers ───────────────────────────────────────────────────────

    @on_event("content.tool.added")
    async def on_tool_added(self, event) -> None:
        uuid = event.data.get("uuid") if isinstance(event.data, dict) else None
        if not uuid:
            return
        await self._safe_evaluate(uuid, "tool")

    @on_event("content.skill.added")
    async def on_skill_added(self, event) -> None:
        uuid = event.data.get("uuid") if isinstance(event.data, dict) else None
        if not uuid:
            return
        await self._safe_evaluate(uuid, "skill")

        # For skills, also evaluate referenced tools and snippets.
        # Import flows write tools/snippets directly without emitting per-object events.
        try:
            skill_obj = await self.store.get_skill(uuid)
        except Exception:
            skill_obj = None
        if skill_obj:
            for tool_uuid in skill_obj.get("tool_uuids") or []:
                await self._safe_evaluate(tool_uuid, "tool")
            for snippet_uuid in skill_obj.get("snippet_uuids") or []:
                await self._safe_evaluate(snippet_uuid, "snippet")

    @on_event("content.snippet.added")
    async def on_snippet_added(self, event) -> None:
        uuid = event.data.get("uuid") if isinstance(event.data, dict) else None
        if not uuid:
            return
        await self._safe_evaluate(uuid, "snippet")

    async def _safe_evaluate(self, uuid: str, content_type: str) -> None:
        if not self.is_enabled() or self._store is None:
            return
        try:
            await self.evaluate_security(uuid, content_type)
        except Exception as e:
            logger.error(
                f"Auto-security-evaluation failed for {content_type} {uuid}: {e}",
                exc_info=True,
            )

    # ── helpers ──────────────────────────────────────────────────────────────

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

            # NOTE: The in-process version fetched raw tool source code via
            # self.store.tools.read_file(...). The SDK's StoreClient does not
            # expose a raw-file read path yet; if/when it does, re-add here.

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
        """Write security score tag and evaluation text back to the store object.

        Merges into extra["evaluation"]["security"] without wiping quality/performance keys.
        """
        existing_tags = self._strip_score_tags(obj.get("tags") or [])
        obj["tags"] = existing_tags + [f"security-score:{evaluation['security_score']}"]

        if not isinstance(obj.get("extra"), dict):
            obj["extra"] = {}
        if not isinstance(obj["extra"].get("evaluation"), dict):
            obj["extra"]["evaluation"] = {}
        obj["extra"]["evaluation"]["security"] = {
            "score": evaluation["security_score"],
            "evaluation": evaluation["security_evaluation"],
        }

        if content_type == "tool":
            await self.store.update_tool(uuid, obj)
        elif content_type == "skill":
            await self.store.update_skill(uuid, obj)
        elif content_type == "snippet":
            await self.store.update_snippet(uuid, obj)

    async def evaluate_security(self, uuid: str, content_type: str) -> Dict[str, Any]:
        """
        Evaluate a store object's security posture.

        Fetches the full object from the store, sends it to the LLM, then
        stores the score as a tag (security-score:N) and the evaluation text
        in extra["evaluation"]["security"]. Preserves any existing quality/
        performance evaluation keys.

        Args:
            uuid: UUID of the object to evaluate
            content_type: "tool", "skill", or "snippet"

        Returns:
            Dict with security_score (int 1-10) and security_evaluation (str)
        """
        if not self.llm_client:
            raise RuntimeError("LLM client not initialized")
        if self._store is None:
            raise RuntimeError("Store API not available")

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

        logger.info(f"Evaluating security of {content_type} {uuid}: {obj.get('name', 'unnamed')}")

        context = self._build_context(obj, content_type)

        prompt = f"""You are evaluating a {content_type} from a skills store for security posture.

{context}

Evaluate this {content_type} on security and return a JSON object with exactly these two fields:
- security_score: integer 1-10 where 1-3 = critical issues (injection flaws, exposed secrets, no input validation), 4-6 = moderate risks (weak error handling, risky dependencies, missing auth checks), 7-9 = minor issues (best-practice gaps, overly permissive patterns), 10 = no identified issues
- security_evaluation: string (one paragraph explicitly naming each specific vulnerability or concern found, or "No security issues identified." if the score is 10)

Return ONLY the JSON object, no other text."""

        logger.debug(f"Calling LLM for security evaluation of {content_type} {uuid}")
        response = await self.llm_client.generate_async(prompt=prompt)
        logger.info(f"Received LLM response ({len(response)} chars)")

        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start < 0 or end <= start:
                raise ValueError("No JSON object found in LLM response")
            evaluation = json.loads(response[start:end])

            for field in ("security_score", "security_evaluation"):
                if field not in evaluation:
                    raise ValueError(f"Missing field in LLM response: {field}")

            evaluation["security_score"] = int(evaluation["security_score"])

        except Exception as e:
            logger.warning(f"Failed to parse LLM security evaluation response: {e}")
            raise RuntimeError(f"Failed to parse LLM response: {str(e)}")

        await self._write_security_to_store(uuid, content_type, obj, evaluation)
        logger.info(
            f"Security evaluation stored for {content_type} {uuid}: "
            f"security={evaluation['security_score']}"
        )

        return evaluation

    # ── router ───────────────────────────────────────────────────────────────

    def get_router(self):
        """Register plugin routes."""
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel

        router = APIRouter(prefix=f"/plugins/{self.manifest.slug}", tags=[self.manifest.slug])

        class EvaluateRequest(BaseModel):
            uuid: str
            content_type: str  # "tool", "skill", or "snippet"

        @router.post("/evaluate")
        async def evaluate_endpoint(request: EvaluateRequest):
            """Evaluate a store object and store the security score."""
            if not self.is_enabled():
                raise HTTPException(status_code=503, detail=self._status_message)

            if request.content_type not in ("tool", "skill", "snippet"):
                raise HTTPException(
                    status_code=400,
                    detail="content_type must be 'tool', 'skill', or 'snippet'",
                )

            try:
                result = await self.evaluate_security(
                    uuid=request.uuid,
                    content_type=request.content_type,
                )
                return {"success": True, "uuid": request.uuid, **result}
            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                logger.error(
                    f"Failed to evaluate security of {request.content_type} {request.uuid}: {e}",
                    exc_info=True,
                )
                raise HTTPException(status_code=500, detail=str(e))

        return router

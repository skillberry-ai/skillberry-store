"""Skill deduplication plugin — detects semantically duplicate skills via LLM."""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from skillberry_plugin_sdk import PluginLifecycleBase, on_event

logger = logging.getLogger(__name__)


class SkillberryPluginDedupe(PluginLifecycleBase):
    """Out-of-process plugin that detects duplicate skills using a single LLM call."""

    manifest_path = "manifest.yaml"

    def __init__(self):
        super().__init__()
        self._mode = os.getenv("DEDUPE_MODE", "interactive")
        self._pending_decisions: Dict[str, dict] = {}
        self.llm_client = None
        self._status_message = "Initializing..."

    async def on_start(self) -> None:
        try:
            from llm_switchboard import get_llm

            provider_name = os.getenv("LLM_PROVIDER", "openai.async")
            model_name = os.getenv("LLM_MODEL", "gpt-4")

            LLMClientClass = get_llm(provider_name)
            self.llm_client = LLMClientClass(model_name=model_name)
            self._status_message = f"Ready (using {provider_name})"
        except ImportError:
            self._status_message = "Missing dependency: llm-switchboard not installed"
            logger.warning("llm-switchboard not installed, plugin will be disabled")
        except Exception as e:
            self._status_message = f"LLM unavailable: {str(e)}"
            logger.error(f"Failed to initialize LLM client: {e}", exc_info=True)

    async def is_ready(self) -> Dict[str, Any]:
        ready = self.llm_client is not None
        return {
            "ready": ready,
            "missing_config": [] if ready else ["LLM_PROVIDER"],
            "status": self._status_message,
        }

    def is_enabled(self) -> bool:
        return self.llm_client is not None

    def get_status_message(self) -> str:
        return self._status_message

    def get_router(self):
        from fastapi import APIRouter, HTTPException

        router = APIRouter()

        @router.get("/decisions")
        async def list_decisions():
            return list(self._pending_decisions.values())

        @router.post("/decisions/{uuid}/keep")
        async def keep_decision(uuid: str):
            decision = self._pending_decisions.pop(uuid, None)
            if decision is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"No pending decision for skill {uuid}",
                )
            return {
                "message": f"Skill '{decision['skill_name']}' marked as kept. Duplicate tags remain."
            }

        @router.post("/decisions/{uuid}/delete")
        async def delete_decision(uuid: str):
            decision = self._pending_decisions.pop(uuid, None)
            if decision is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"No pending decision for skill {uuid}",
                )
            try:
                await self.store._request("DELETE", f"/skills/{uuid}")
            except Exception:
                logger.error(f"Failed to delete skill {uuid} during dedupe decision", exc_info=True)
            return {"message": f"Skill '{decision['skill_name']}' deleted."}

        return router

    # ── event handlers ────────────────────────────────────────────────────────

    @on_event("content.skill.added")
    @on_event("content.skill.updated")
    async def on_skill_change(self, event) -> None:
        if not self.is_enabled():
            return
        uuid = event.data.get("uuid") if isinstance(event.data, dict) else None
        if not uuid:
            return
        await self._check_for_duplicates(uuid)

    # ── internals ─────────────────────────────────────────────────────────────

    async def _get_candidate_skills(self, trigger_uuid: str) -> List[Dict]:
        """Return original (non-duplicate-tagged) skills other than the trigger skill."""
        all_skills = await self.store.list_skills()
        return [
            s for s in all_skills
            if s.get("uuid") != trigger_uuid
            and not any(t.startswith("duplicate:") for t in (s.get("tags") or []))
        ]

    def _build_prompt(self, skill: Dict, candidates: List[Dict]) -> str:
        """Build the single LLM prompt for duplicate detection."""
        lines = [
            "You are a skill deduplication assistant. Identify whether the new skill is semantically",
            "equivalent or very similar to any of the existing skills.",
            "",
            "Focus on the DESCRIPTION, not the name. Two skills are duplicates if their descriptions",
            "describe essentially the same capability or purpose. Minor wording differences do not",
            "count — the similarity must be very strong.",
            "",
            "New skill:",
            f"  Name: {skill.get('name', '')}",
            f"  Description: {skill.get('description', '')}",
            "",
            "Existing skills:",
        ]
        for i, candidate in enumerate(candidates, 1):
            lines.append(f"  {i}. Name: {candidate.get('name', '')}")
            lines.append(f"     Description: {candidate.get('description', '')}")
        lines.extend([
            "",
            'Return ONLY a JSON array. Each entry must have "name" (the existing skill\'s exact name)',
            'and "reason" (one sentence explaining the similarity). If no duplicates are found,',
            "return [].",
        ])
        return "\n".join(lines)

    def _parse_llm_response(self, response: str) -> List[Dict]:
        """Extract and validate the JSON array from the LLM response."""
        match = re.search(r'\[.*\]', response, re.DOTALL)
        if not match:
            raise ValueError(f"No JSON array found in LLM response: {response!r}")
        raw = json.loads(match.group())
        return [
            {"name": item["name"], "reason": item["reason"]}
            for item in raw
            if "name" in item and "reason" in item
        ]

    async def _apply_duplicate_findings(self, uuid: str, findings: List[Dict]) -> None:
        """Write duplicate tags and analysis to the skill. Additive — never removes."""
        if not findings:
            return

        tags = [f"duplicate:{f['name']}" for f in findings]
        try:
            await self.store.update_skill_tags(uuid, tags)
        except Exception:
            logger.error(f"Failed to update tags for skill {uuid}", exc_info=True)

        skill = await self.store.get_skill(uuid)
        if skill is None:
            logger.error(f"Skill {uuid} not found when writing duplicate_analysis")
            return

        existing_extra = dict(skill.get("extra") or {})
        existing_analysis = dict(existing_extra.get("duplicate_analysis") or {})
        for finding in findings:
            existing_analysis[finding["name"]] = finding["reason"]
        existing_extra["duplicate_analysis"] = existing_analysis
        skill["extra"] = existing_extra

        try:
            await self.store.update_skill(uuid, skill)
        except Exception:
            logger.error(f"Failed to update metadata for skill {uuid}", exc_info=True)

    async def _check_for_duplicates(self, uuid: str) -> None:
        """Main handler: fetch skill, compare against candidates, tag if duplicates found."""
        if not self.is_enabled():
            return

        skill = await self.store.get_skill(uuid)
        if skill is None:
            logger.warning(f"Skill {uuid} not found, skipping dedupe check")
            return

        description = skill.get("description") or ""
        if len(description) < 10:
            logger.debug(f"Skill {uuid} has no/short description, skipping dedupe check")
            return

        candidates = await self._get_candidate_skills(uuid)
        if not candidates:
            logger.debug(f"No original skills to compare against for {uuid}")
            return

        prompt = self._build_prompt(skill, candidates)

        try:
            response = await self.llm_client.generate_async(prompt=prompt)
        except Exception as e:
            logger.error(f"LLM call failed for skill {uuid}: {e}", exc_info=True)
            return

        try:
            findings = self._parse_llm_response(response)
        except Exception as e:
            logger.error(
                f"Failed to parse LLM response for skill {uuid}: {e}. Raw: {response!r}",
                exc_info=True,
            )
            return

        if findings:
            await self._apply_duplicate_findings(uuid, findings)
            if self._mode == "interactive":
                self._pending_decisions[uuid] = {
                    "uuid": uuid,
                    "skill_name": skill.get("name", uuid),
                    "duplicates": findings,
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                }
            logger.info(
                f"Skill {uuid} tagged with {len(findings)} duplicate(s): "
                f"{[f['name'] for f in findings]}"
            )

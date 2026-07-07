"""Kagenti Approver plugin — labels skills as kagenti-approved based on score-tag criteria."""

from __future__ import annotations

import logging
import os
import re
from typing import Dict, List, Tuple

from skillberry_plugin_sdk import PluginLifecycleBase, on_event

logger = logging.getLogger(__name__)

APPROVED_TAG = "kagenti-approved"
DEFAULT_CRITERIA = "security-score>=7"

_OPERATOR_RE = re.compile(r"^(.+?)(>=|>|<=|<|!=|=)(\S+)$")


def parse_criteria(criteria_str: str) -> List[List[Tuple[str, str, float]]]:
    """Parse ``a>=1,b>=2|c>=3`` into OR-groups of AND-conditions."""
    if not criteria_str.strip():
        return []
    result: List[List[Tuple[str, str, float]]] = []
    for or_group_str in criteria_str.split("|"):
        conditions: List[Tuple[str, str, float]] = []
        for condition_str in or_group_str.split(","):
            condition_str = condition_str.strip()
            if not condition_str:
                continue
            match = _OPERATOR_RE.match(condition_str)
            if not match:
                logger.warning("Kagenti approver: skipping malformed condition: %r", condition_str)
                continue
            tag, operator, threshold_str = match.group(1), match.group(2), match.group(3)
            try:
                threshold = float(threshold_str)
            except ValueError:
                logger.warning(
                    "Kagenti approver: skipping non-numeric threshold: %r", condition_str
                )
                continue
            conditions.append((tag.strip(), operator, threshold))
        if conditions:
            result.append(conditions)
    return result


def extract_scores(tags: List[str]) -> Dict[str, float]:
    """Parse tags like ``security-score:9`` into ``{'security-score': 9.0}``."""
    scores: Dict[str, float] = {}
    for tag in tags:
        if ":" not in tag:
            continue
        key, _, value_str = tag.partition(":")
        if not value_str:
            continue
        try:
            scores[key] = float(value_str)
        except ValueError:
            pass
    return scores


def evaluate_criteria(
    or_groups: List[List[Tuple[str, str, float]]],
    score_map: Dict[str, float],
) -> bool:
    if not or_groups:
        return False
    return any(_group_passes(group, score_map) for group in or_groups)


def _group_passes(
    conditions: List[Tuple[str, str, float]],
    score_map: Dict[str, float],
) -> bool:
    for tag, operator, threshold in conditions:
        value = score_map.get(tag)
        if value is None:
            return False
        if operator == ">=" and not (value >= threshold):
            return False
        if operator == ">" and not (value > threshold):
            return False
        if operator == "<=" and not (value <= threshold):
            return False
        if operator == "<" and not (value < threshold):
            return False
        if operator == "=" and not (value == threshold):
            return False
        if operator == "!=" and not (value != threshold):
            return False
    return True


class SkillberryPluginKagentiApprover(PluginLifecycleBase):
    """Out-of-process plugin that labels skills as kagenti-approved."""

    manifest_path = "manifest.yaml"

    @on_event("content.skill.added")
    @on_event("content.skill.updated")
    async def on_skill_change(self, event) -> None:
        uuid = event.data.get("uuid") if isinstance(event.data, dict) else None
        if not uuid:
            return
        await self._evaluate_skill(uuid)

    def _load_criteria(self) -> List[List[Tuple[str, str, float]]]:
        raw = os.environ.get("KAGENTI_CRITERIA", DEFAULT_CRITERIA)
        return parse_criteria(raw)

    async def _evaluate_skill(self, uuid: str) -> None:
        skill = await self.store.get_skill(uuid)
        if skill is None:
            logger.warning("Kagenti approver: skill %s not found, skipping", uuid)
            return

        tags: List[str] = list(skill.get("tags") or [])
        score_map = extract_scores(tags)
        or_groups = self._load_criteria()
        approved = evaluate_criteria(or_groups, score_map)
        has_tag = APPROVED_TAG in tags

        if approved and not has_tag:
            logger.info("Kagenti approver: approving skill %s", uuid)
            await self.store.update_skill_tags(uuid, [APPROVED_TAG])
        elif not approved and has_tag:
            logger.info("Kagenti approver: revoking approval for skill %s", uuid)
            skill["tags"] = [t for t in tags if t != APPROVED_TAG]
            await self.store.update_skill(uuid, skill)

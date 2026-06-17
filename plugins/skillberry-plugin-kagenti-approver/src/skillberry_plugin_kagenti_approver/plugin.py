"""Kagenti Approver plugin — labels skills as kagenti-approved based on score-tag criteria."""

import os
import re
import logging
from typing import Any, Dict, List, Optional, Tuple

from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType

logger = logging.getLogger(__name__)

APPROVED_TAG = "kagenti-approved"
DEFAULT_CRITERIA = "security-score>=9"

_OPERATOR_RE = re.compile(r"^(.+?)(>=|>|<=|<|!=|=)(\S+)$")


def parse_criteria(criteria_str: str) -> List[List[Tuple[str, str, float]]]:
    """Parse criteria string into OR-groups of AND-conditions.

    Returns a list of OR-groups. Each OR-group is a list of (tag, operator, threshold) tuples.
    OR-groups are separated by '|'; AND-conditions within a group are separated by ','.
    Malformed or non-numeric conditions are skipped. Empty/all-malformed OR-groups are dropped.

    Example:
        "security-score>=9,performance-score>=8|security-score>=10"
        -> [
             [("security-score", ">=", 9.0), ("performance-score", ">=", 8.0)],
             [("security-score", ">=", 10.0)],
           ]
    """
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
                logger.warning(f"Kagenti approver: skipping malformed condition: {condition_str!r}")
                continue
            tag, operator, threshold_str = match.group(1), match.group(2), match.group(3)
            try:
                threshold = float(threshold_str)
            except ValueError:
                logger.warning(
                    f"Kagenti approver: skipping condition with non-numeric threshold: {condition_str!r}"
                )
                continue
            conditions.append((tag.strip(), operator, threshold))
        if conditions:
            result.append(conditions)
    return result


def extract_scores(tags: List[str]) -> Dict[str, float]:
    """Parse tags like 'security-score:9' into {'security-score': 9.0}.

    Tags without a colon or with non-numeric values are ignored.
    """
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
    """Return True if any OR-group has all its AND-conditions satisfied."""
    if not or_groups:
        return False
    for group in or_groups:
        if _group_passes(group, score_map):
            return True
    return False


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
        elif operator == ">" and not (value > threshold):
            return False
        elif operator == "<=" and not (value <= threshold):
            return False
        elif operator == "<" and not (value < threshold):
            return False
        elif operator == "=" and not (value == threshold):
            return False
        elif operator == "!=" and not (value != threshold):
            return False
    return True


class SkillberryPluginKagentiApprover(PluginBase):
    """Plugin that labels skills as kagenti-approved when their score tags meet criteria."""

    def __init__(self):
        super().__init__()
        self._metadata = PluginMetadata(
            name="Kagenti Approver",
            version="0.1.0",
            description="Automatically label skills as kagenti-approved based on score-tag criteria",
            plugin_type=PluginType.EVALUATOR,
        )
        self._register_event_handlers()

    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata

    def is_enabled(self) -> bool:
        return True

    def get_router(self):
        return None

    def get_cli_commands(self) -> Optional[Dict[str, Any]]:
        return None

    def get_ui_config(self) -> Optional[Dict[str, Any]]:
        return None

    def _load_criteria(self) -> List[List[Tuple[str, str, float]]]:
        raw = os.environ.get("KAGENTI_CRITERIA", DEFAULT_CRITERIA)
        return parse_criteria(raw)

    def _register_event_handlers(self) -> None:
        from skillberry_store.plugins.events import _event_handlers

        for event_name in ("content_added:skill", "content_updated:skill"):
            async def _handle(uuid: str):
                if self._store_api is None:
                    return
                await self._evaluate_skill(uuid)

            if event_name not in _event_handlers:
                _event_handlers[event_name] = []
            _event_handlers[event_name].append(_handle)

    async def _evaluate_skill(self, uuid: str) -> None:
        """Fetch skill, evaluate criteria, add or remove APPROVED_TAG.

        - Criteria met + tag absent  → add APPROVED_TAG (union write via update_skill_tags)
        - Criteria met + tag present → no-op (avoid unnecessary write)
        - Criteria not met + tag present → remove APPROVED_TAG (full write via update_skill)
        - Criteria not met + tag absent  → no-op
        """
        skill = self.store.get_skill(uuid)
        if skill is None:
            logger.warning(f"Kagenti approver: skill {uuid} not found, skipping")
            return

        tags: List[str] = list(skill.get("tags") or [])
        score_map = extract_scores(tags)
        or_groups = self._load_criteria()
        approved = evaluate_criteria(or_groups, score_map)
        has_tag = APPROVED_TAG in tags

        if approved and not has_tag:
            logger.info(f"Kagenti approver: approving skill {uuid}")
            self.store.update_skill_tags(uuid, [APPROVED_TAG])
        elif not approved and has_tag:
            logger.info(f"Kagenti approver: revoking approval for skill {uuid}")
            skill["tags"] = [t for t in tags if t != APPROVED_TAG]
            self.store.update_skill(uuid, skill)

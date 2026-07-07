"""Event publishing helpers.

SBS publishes content-change events onto the SSE hub; out-of-process plugin
subprocesses subscribe via ``GET /events/stream``. The in-process handler
registry that predated Stage 6 is gone — this module now exists only to
translate service-layer content mutations into ``content.<type>.<action>``
topics on the hub.
"""

from __future__ import annotations

import logging
from typing import Dict

logger = logging.getLogger(__name__)


def _publish_to_sse(topic: str, payload: Dict[str, str]) -> None:
    try:
        from skillberry_store.plugins.sse_hub import get_hub

        get_hub().publish(topic, payload)
    except Exception:  # pragma: no cover - defensive
        logger.debug("SSE publish failed", exc_info=True)


def emit_content_added(content_type: str, uuid: str) -> None:
    _publish_to_sse(f"content.{content_type}.added", {"uuid": uuid, "type": content_type})


def emit_content_updated(content_type: str, uuid: str) -> None:
    _publish_to_sse(f"content.{content_type}.updated", {"uuid": uuid, "type": content_type})


def emit_content_deleted(content_type: str, uuid: str) -> None:
    _publish_to_sse(f"content.{content_type}.deleted", {"uuid": uuid, "type": content_type})

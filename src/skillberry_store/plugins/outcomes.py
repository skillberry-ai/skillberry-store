"""Recording what happened on a plugin run — three terminal states.

Plugins label successes only. Everything else — nothing scannable, a missing
engine, a crash, and now an authorization denial — used to leave no trace on
the object but a ``logger.error`` line, and was therefore indistinguishable
from "never ran" (plugin-identity §9.1).

Three states, one per run, mutually exclusive:

============ =============================================================
``result``   the plugin reached a judgement. **Not a new tag** — it is
             whatever the plugin already writes (``sast:clean``,
             ``sast:high:2``), so nothing gets layered on top of it. This
             module never writes it.
``skip``     the content did not warrant analysis.
``error``    the analysis could not be performed.
============ =============================================================

The discriminator for plugin authors, since the last two are easy to
confuse: **skip means the content didn't warrant analysis; error means the
analysis couldn't be performed.** A non-Python file is ``skip``; Bandit not
being installed is ``error``.

Keeping the vocabulary closed matters more than it looks: ``services/facets``
enumerates every unique tag in the store to populate the UI's tag picker, so
a tag family that grew one entry per failure mode (``sast:denied``,
``sast:no-owner``, …) would degrade that filter as it grew. Three fixed
states keep the picker stable while ``extra`` absorbs unbounded diagnostic
detail. Cause belongs in the block; category belongs in the tag.

**The framework records the outcome, not the plugin.** Writing an outcome tag
is itself an update to the object, so a plugin denied ``update`` cannot record
its own denial and a plugin with no tenant at all cannot write anything — the
two states most worth recording are exactly the two that cannot record
themselves. ``record_outcome`` sits above plugin code, at the ``_admit`` raise
site, and writes **through the service handler directly**: going through
``StoreAPI.update_skill`` would re-enter the very ``_admit`` call that just
failed, and going through the service layer would emit ``content_updated``
and re-enter the handler whose failure is being recorded.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

OUTCOME_RESULT = "result"
OUTCOME_SKIP = "skip"
OUTCOME_ERROR = "error"

#: States this module writes. ``result`` is the plugin's own to write.
RECORDABLE_OUTCOMES = (OUTCOME_SKIP, OUTCOME_ERROR)


def outcome_tag(slug: str, state: str) -> str:
    """The tag for one outcome, in the plugin's own tag family.

    Same family the plugin already strips on re-scan (``sast:`` for
    ``_strip_sast_tags``), so a later successful run replaces a stale failure
    rather than accumulating alongside it.
    """
    return f"{slug}:{state}"


def record_outcome(
    services: Dict[str, Any],
    slug: Optional[str],
    uuid: Optional[str],
    state: str,
    reason: str,
) -> bool:
    """Label ``uuid`` with a plugin outcome. Returns whether anything was written.

    Best-effort by construction: it runs on the failure path, so it must never
    raise over the failure it is recording. ``False`` means there was nothing
    to label (no uuid, no such object) or the write itself failed — both are
    logged.
    """
    if state not in RECORDABLE_OUTCOMES:
        raise ValueError(
            f"record_outcome: {state!r} is not recordable "
            f"(expected one of {RECORDABLE_OUTCOMES}; 'result' is the "
            f"plugin's own tag to write)"
        )
    if not slug:
        logger.warning(
            "Plugin outcome %s not recorded (no plugin slug): %s", state, reason
        )
        return False
    if not uuid:
        # A create_* or list_* call has no object to label. The log line is
        # the only trace available, which is why this is a warning.
        logger.warning(
            "Plugin %r outcome %s not recorded (no object uuid): %s",
            slug,
            state,
            reason,
        )
        return False

    for handler in _candidate_handlers(services):
        obj = _try_read(handler, uuid)
        if obj is None:
            continue
        try:
            _apply(obj, slug, state, reason)
            handler.write_dict(uuid, obj)
            logger.info(
                "Plugin %r outcome %s recorded on %s: %s", slug, state, uuid, reason
            )
            return True
        except Exception as e:  # noqa: BLE001 - never mask the original failure
            logger.error(
                "Plugin %r could not record outcome %s on %s: %s",
                slug,
                state,
                uuid,
                e,
            )
            return False

    logger.warning(
        "Plugin %r outcome %s not recorded (object %s not found): %s",
        slug,
        state,
        uuid,
        reason,
    )
    return False


def _candidate_handlers(services: Dict[str, Any]) -> List[Any]:
    """The object handlers an outcome could belong to.

    ``_admit`` knows the resource it denied, but the uuid is what identifies
    the object, and probing is cheaper and less brittle than threading a
    content type through every call site.
    """
    handlers = []
    for key in ("skills", "tools", "snippets"):
        service = services.get(key)
        handler = getattr(service, "handler", None) if service else None
        if handler is not None:
            handlers.append(handler)
    return handlers


def _try_read(handler: Any, uuid: str) -> Optional[Dict[str, Any]]:
    try:
        obj = handler.read_dict(uuid)
    except Exception:  # noqa: BLE001 - a miss raises HTTPException(404) here
        return None
    return obj if isinstance(obj, dict) else None


def _apply(obj: Dict[str, Any], slug: str, state: str, reason: str) -> None:
    """Replace any prior outcome for this plugin with the new one, in place."""
    stale = {outcome_tag(slug, s) for s in RECORDABLE_OUTCOMES}
    tags = [t for t in (obj.get("tags") or []) if t not in stale]
    tags.append(outcome_tag(slug, state))
    obj["tags"] = tags

    if not isinstance(obj.get("extra"), dict):
        obj["extra"] = {}
    if not isinstance(obj["extra"].get(slug), dict):
        obj["extra"][slug] = {}
    obj["extra"][slug]["outcome"] = {
        "state": state,
        "reason": reason,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }

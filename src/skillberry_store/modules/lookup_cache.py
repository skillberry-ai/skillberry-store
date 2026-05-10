import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from fastapi import HTTPException

from skillberry_store.modules.file_handler import FileHandler

logger = logging.getLogger(__name__)


@dataclass
class LookupCache:
    skills_by_uuid: Dict[str, dict] = field(default_factory=dict)
    tools_by_uuid: Dict[str, dict] = field(default_factory=dict)
    snippets_by_uuid: Dict[str, dict] = field(default_factory=dict)


def load_json_objects(handler: FileHandler, object_label: str) -> List[dict]:
    """Load valid JSON object documents from a file-backed store."""
    objects: List[dict] = []

    for filename in handler.list_files():
        if not filename.endswith(".json"):
            continue

        try:
            content = handler.read_file(filename, raw_content=True)
            if not isinstance(content, str):
                logger.warning(
                    f"Unexpected non-string content for {object_label} file '{filename}'"
                )
                continue

            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                logger.warning(
                    f"Skipping {object_label} file '{filename}' because JSON root is not an object"
                )
                continue

            objects.append(parsed)
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning(f"Error loading {object_label} file '{filename}': {exc}")

    return objects


def build_uuid_cache(objects: List[dict], object_label: str) -> Dict[str, dict]:
    """Build a UUID-to-object cache from a list of parsed JSON objects."""
    uuid_cache: Dict[str, dict] = {}

    for obj in objects:
        object_uuid = obj.get("uuid")
        if not object_uuid:
            logger.warning(
                f"Skipping {object_label} object without uuid: {obj.get('name', '<unknown>')}"
            )
            continue
        uuid_cache[object_uuid] = obj

    return uuid_cache


def build_lookup_cache(
    skills_handler: Optional[FileHandler] = None,
    tools_handler: Optional[FileHandler] = None,
    snippets_handler: Optional[FileHandler] = None,
) -> LookupCache:
    """Build UUID caches for the provided stores."""
    cache = LookupCache()

    if skills_handler is not None:
        cache.skills_by_uuid = build_uuid_cache(
            load_json_objects(skills_handler, "skill"),
            "skill",
        )

    if tools_handler is not None:
        cache.tools_by_uuid = build_uuid_cache(
            load_json_objects(tools_handler, "tool"),
            "tool",
        )

    if snippets_handler is not None:
        cache.snippets_by_uuid = build_uuid_cache(
            load_json_objects(snippets_handler, "snippet"),
            "snippet",
        )

    return cache


# Made with Bob

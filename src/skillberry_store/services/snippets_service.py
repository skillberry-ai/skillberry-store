"""Business logic for snippet CRUD operations."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from prometheus_client import Counter

from skillberry_store.modules.object_handler import ObjectHandler
from skillberry_store.plugins.events import (
    emit_content_added,
    emit_content_deleted,
    emit_content_updated,
)
from skillberry_store.services.exceptions import ObjectInUseError
from skillberry_store.utils.utils import generate_or_validate_uuid

if TYPE_CHECKING:
    from skillberry_store.modules.lifecycle import LifecycleState

logger = logging.getLogger(__name__)

# observability - metrics
prom_prefix = "sts_service_snippets_"
create_snippet_counter = Counter(
    f"{prom_prefix}create_snippet_counter", "Count number of snippet create operations"
)
list_snippets_counter = Counter(
    f"{prom_prefix}list_snippets_counter", "Count number of snippet list operations"
)
get_snippet_counter = Counter(
    f"{prom_prefix}get_snippet_counter", "Count number of snippet get operations"
)
delete_snippet_counter = Counter(
    f"{prom_prefix}delete_snippet_counter", "Count number of snippet delete operations"
)
update_snippet_counter = Counter(
    f"{prom_prefix}update_snippet_counter", "Count number of snippet update operations"
)
search_snippets_counter = Counter(
    f"{prom_prefix}search_snippets_counter", "Count number of snippet search operations"
)


class SnippetsService:
    """Service layer for snippet CRUD operations.
    
    Provides business logic for managing snippets, which are reusable text blocks
    that can be referenced by skills.
    
    Attributes:
        handler: ObjectHandler for snippet persistence operations.
        descriptions: accessed via ``handler.descriptions`` (not stored as a separate attribute).
    """
    
    def __init__(self, handler: ObjectHandler):
        """Initialize the SnippetsService.
        
        Args:
            handler: ObjectHandler instance for snippet operations.
        """
        self.handler = handler


    def _resolve_uuid(self, uuid_or_name: str) -> str:
        """Resolve a snippet identifier to its UUID.
        
        Args:
            uuid_or_name: Snippet UUID or name to resolve.
            
        Returns:
            str: The resolved UUID.
            
        Raises:
            KeyError: If snippet not found.
        """
        try:
            return self.handler.resolve_to_uuid_or_error(uuid_or_name)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"Snippet '{uuid_or_name}' not found")
            raise

    def add_dependent(
        self, referencing_type: str, referencing_uuid: str, referenced_snippet_uuids: List[str]
    ) -> None:
        """Register that ``referencing_uuid`` depends on each UUID in ``referenced_snippet_uuids``.

        Called by ``SkillsService`` when it creates or updates a skill that references snippets.

        Args:
            referencing_type: Object type of the referencing object (e.g. ``"skill"``).
            referencing_uuid: UUID of the referencing object.
            referenced_snippet_uuids: UUIDs of the snippets being depended on.
        """
        self.handler.dependency_manager.add(
            referencing_type, referencing_uuid, referenced_snippet_uuids
        )

    def remove_dependent(self, referencing_type: str, referencing_uuid: str) -> None:
        """Remove all dependency records where ``referencing_uuid`` is the referencing side.

        Called when the referencing object is updated or deleted.

        Args:
            referencing_type: Object type of the referencing object.
            referencing_uuid: UUID of the referencing object.
        """
        self.handler.dependency_manager.remove_referencing(referencing_type, referencing_uuid)

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new snippet.
        
        Creates a snippet entry with text content and updates caches and indexes.
        
        Args:
            data: Snippet metadata dictionary (name, description, content, etc.).
            
        Returns:
            Dict[str, Any]: The created snippet data with UUID and timestamps.
            
        Raises:
            ValueError: If snippet with the same UUID already exists.
        """
        create_snippet_counter.inc()
        try:
            data["uuid"] = generate_or_validate_uuid(data.get("uuid"))
            if self.handler.object_exists(data["uuid"]):
                raise ValueError(
                    f"Snippet with UUID '{data['uuid']}' already exists"
                )
            now = datetime.now(timezone.utc).isoformat()
            data.setdefault("created_at", now)
            data["modified_at"] = now
            if data.get("name"):
                data["parent"] = self.handler.get_cache_parent_for_head(
                    data["uuid"], data["name"]
                )
            self.handler.write_dict(data["uuid"], data)
            if data.get("name"):
                self.handler.update_cache(data["uuid"], new_name=data["name"])
            if self.handler.descriptions and data.get("description"):
                self.handler.descriptions.write_description(data["uuid"], data["description"])
            emit_content_added("snippet", data["uuid"])
            logger.info(
                f"Snippet '{data.get('name')}' created with UUID {data['uuid']}"
            )
            return data
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error creating snippet '{data.get('name')}': {e}")
            raise

    def _safe_read(self, uuid: str, label: str) -> Dict[str, Any]:
        """Safely read a snippet dictionary with error handling.
        
        Args:
            uuid: Snippet UUID to read.
            label: Human-readable label for error messages.
            
        Returns:
            Dict[str, Any]: Snippet metadata dictionary.
            
        Raises:
            KeyError: If snippet not found.
        """
        try:
            return self.handler.read_dict(uuid)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"Snippet '{label}' not found")
            raise

    def get(self, uuid_or_name: str) -> Dict[str, Any]:
        """Get snippet metadata by UUID or name.

        Args:
            uuid_or_name: Snippet UUID or name.

        Returns:
            Dict[str, Any]: Snippet metadata dictionary.

        Raises:
            KeyError: If snippet not found.
        """
        get_snippet_counter.inc()
        try:
            uuid = self._resolve_uuid(uuid_or_name)
            with self.handler.read_lock(uuid):
                return self._safe_read(uuid, uuid_or_name)
        except KeyError:
            raise
        except Exception as e:
            logger.error(f"Error retrieving snippet '{uuid_or_name}': {e}")
            raise

    def list_all(
        self,
        filters: Optional[Dict] = None,
        fields: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List all snippets with optional filtering and field selection.

        Args:
            filters: Optional dictionary of field:value pairs to filter by.
            fields: Optional field-selection spec (``None`` /
                ``"narrow"`` / ``"wide"`` / ``"full"`` / CSV
                allowlist). ``None`` and ``"narrow"`` both resolve to
                the narrow preset (the default). See
                :mod:`skillberry_store.services.field_selection`.

        Returns:
            List[Dict[str, Any]]: List of snippet metadata dictionaries,
                sorted by modified_at descending. Fields are filtered
                according to ``fields``.
        """
        from skillberry_store.services.field_selection import (
            parse_fields_spec,
            select_items_fields,
        )

        list_snippets_counter.inc()
        try:
            items = self.handler.list_all_dicts()
            if filters:
                items = [
                    i for i in items if all(i.get(k) == v for k, v in filters.items())
                ]
            items.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
            allow = parse_fields_spec(fields, "snippet")
            return select_items_fields(items, allow)
        except Exception as e:
            logger.error(f"Error listing snippets: {e}")
            raise

    def search(
        self,
        search_term: str,
        max_number_of_results: int = 5,
        similarity_threshold: float = 1.0,
        manifest_filter: str = ".",
        lifecycle_state: Optional["LifecycleState"] = None,
        fields: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search snippets by semantic similarity to a search term.

        Performs a vector-similarity search over snippet descriptions, then filters
        by similarity threshold, manifest properties, and lifecycle state, and
        returns matched names with similarity scores sorted by ``modified_at``
        (most recent first).

        Args:
            search_term: Free-text query to match against snippet descriptions.
            max_number_of_results: Upper bound on candidates returned by the
                vector index before threshold filtering.
            similarity_threshold: Maximum allowed similarity score (lower is
                more similar). Candidates above this score are discarded.
            manifest_filter: Manifest property filter expression
                (e.g. ``"tags:python"``, ``"state:approved"``).
            lifecycle_state: Lifecycle state filter. Defaults to
                ``LifecycleState.ANY`` when ``None`` is passed.
            fields: Optional field-selection spec — same grammar as
                :meth:`list_all` (``None`` / ``"narrow"`` / ``"wide"``
                / ``"full"`` / CSV allowlist). Each match is a
                field-selected snippet dict with ``similarity_score``
                merged in. Default (``None``) resolves to ``"narrow"``
                — the minimal UI listing set.

        Returns:
            List[Dict[str, Any]]: Matches sorted by ``modified_at`` desc.
                Each entry is a field-selected snippet dict plus a
                ``similarity_score`` key.

        Raises:
            RuntimeError: If the service was constructed without a
                ``Description`` instance (search index unavailable).
        """
        from skillberry_store.modules.lifecycle import LifecycleState
        from skillberry_store.fast_api.search_filters import apply_search_filters
        from skillberry_store.services.field_selection import (
            parse_fields_spec,
            select_item_fields,
        )

        search_snippets_counter.inc()
        try:
            if lifecycle_state is None:
                lifecycle_state = LifecycleState.ANY
            if not self.handler.descriptions:
                raise RuntimeError("Snippet search is not available")

            matched = self.handler.descriptions.search_description(
                search_term=search_term, k=max_number_of_results
            )
            filtered = [
                m
                for m in matched
                if float(m["similarity_score"]) <= similarity_threshold
            ]
            candidates: List[Dict[str, Any]] = []
            for m in filtered:
                name = m.get("filename") or m.get("name")
                if not name:
                    continue
                try:
                    fetched = self.get(name)
                    candidate = dict(fetched)
                    candidate["similarity_score"] = m.get("similarity_score", 0.0)
                    candidates.append(candidate)
                except Exception:
                    pass
            result_snippets = apply_search_filters(
                candidates,
                manifest_filter=manifest_filter,
                lifecycle_state=lifecycle_state,
            )
            result_snippets.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
            allow = parse_fields_spec(fields, "snippet")
            return [
                {
                    **select_item_fields(s, allow),
                    "similarity_score": s.get("similarity_score", 0.0),
                }
                for s in result_snippets
                if s.get("name")
            ]
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Error searching snippets: {e}")
            raise

    def update(self, uuid_or_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing snippet's metadata and content.

        Merges new data with existing snippet data, updates timestamps, caches,
        and description indexes as needed.

        Args:
            uuid_or_name: Snippet UUID or name to update.
            data: Dictionary of fields to update.

        Returns:
            Dict[str, Any]: The updated snippet metadata.

        Raises:
            KeyError: If snippet not found.
        """
        update_snippet_counter.inc()
        try:
            uuid = self._resolve_uuid(uuid_or_name)
            with self.handler.write_lock(uuid):
                existing = self.handler.read_dict(uuid)
                old_name = existing.get("name")
                old_parent = existing.get("parent")
                new_name = data.get("name") or old_name
                if new_name:
                    data["parent"] = self.handler.get_cache_parent_for_head(uuid, new_name)
                merged = {**existing, **data}
                merged["uuid"] = existing.get("uuid", uuid)
                merged["created_at"] = existing.get("created_at")
                merged["modified_at"] = datetime.now(timezone.utc).isoformat()
                self.handler.write_dict(uuid, merged)
                if new_name:
                    self.handler.update_cache(
                        uuid, new_name=new_name, old_name=old_name, old_parent=old_parent
                    )
                if self.handler.descriptions and merged.get("description"):
                    self.handler.descriptions.write_description(uuid, merged["description"])
                emit_content_updated("snippet", uuid)
                logger.info(f"Snippet '{uuid_or_name}' updated")
                return merged
        except KeyError:
            raise
        except Exception as e:
            logger.error(f"Error updating snippet '{uuid_or_name}': {e}")
            raise

    def delete(self, uuid_or_name: str) -> Dict[str, Any]:
        """Delete a snippet.

        Removes the snippet metadata, cache entries, and description indexes.

        Args:
            uuid_or_name: Snippet UUID or name to delete.

        Returns:
            Dict[str, Any]: ``{"uuid": <deleted-snippet-uuid>}``.

        Raises:
            KeyError: If snippet not found.
        """
        delete_snippet_counter.inc()
        try:
            uuid = self._resolve_uuid(uuid_or_name)
            with self.handler.write_lock(uuid):
                dependents = self.handler.dependency_manager.get_dependents(uuid)
                if dependents:
                    raise ObjectInUseError("snippet", uuid, dependents)
                try:
                    d = self.handler.read_dict(uuid)
                    name, parent = d.get("name"), d.get("parent")
                except Exception:
                    name, parent = None, None
                if uuid and name:
                    self.handler.update_cache(
                        uuid, new_name=None, old_name=name, old_parent=parent
                    )
                self.handler.delete_object(uuid)
                if self.handler.descriptions:
                    try:
                        self.handler.descriptions.delete_description(uuid)
                    except Exception as e:
                        logger.warning(
                            f"Could not delete snippet description for {uuid}: {e}"
                        )
                emit_content_deleted("snippet", uuid)
                logger.info(f"Snippet '{uuid_or_name}' deleted")
                return {"uuid": uuid}
        except (KeyError, ObjectInUseError):
            raise
        except Exception as e:
            logger.exception(f"Error deleting snippet '{uuid_or_name}': {e}")
            raise

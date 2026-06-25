"""Business logic for virtual MCP server CRUD operations."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from prometheus_client import Counter

from skillberry_store.modules.object_handler import ObjectHandler
from skillberry_store.utils.utils import generate_or_validate_uuid

if TYPE_CHECKING:
    from skillberry_store.modules.description import Description
    from skillberry_store.modules.lifecycle import LifecycleState
    from skillberry_store.modules.vmcp_server_manager import VirtualMcpServerManager

logger = logging.getLogger(__name__)

# observability - metrics
prom_prefix = "sts_service_vmcp_"
create_vmcp_counter = Counter(
    f"{prom_prefix}create_vmcp_counter", "Count number of vmcp create operations"
)
list_vmcp_counter = Counter(
    f"{prom_prefix}list_vmcp_counter", "Count number of vmcp list operations"
)
get_vmcp_counter = Counter(
    f"{prom_prefix}get_vmcp_counter", "Count number of vmcp get operations"
)
delete_vmcp_counter = Counter(
    f"{prom_prefix}delete_vmcp_counter", "Count number of vmcp delete operations"
)
update_vmcp_counter = Counter(
    f"{prom_prefix}update_vmcp_counter", "Count number of vmcp update operations"
)
start_vmcp_counter = Counter(
    f"{prom_prefix}start_vmcp_counter", "Count number of vmcp start operations"
)
search_vmcp_counter = Counter(
    f"{prom_prefix}search_vmcp_counter", "Count number of vmcp search operations"
)


class VmcpService:
    """Service layer for virtual MCP server CRUD operations.

    Provides business logic for managing virtual MCP servers, which expose
    skills as MCP-compatible servers on specified ports. Skill-related lookups
    (e.g. resolving the underlying skill's tools and snippets in
    :meth:`_resolve_skill_uuids`) are routed through
    :func:`skillberry_store.services.registry.get_service`.

    Attributes:
        handler: ObjectHandler for VMCP server persistence operations.
        server_manager: VirtualMcpServerManager for runtime server management.
        descriptions: Optional Description instance for semantic search indexing.
    """

    def __init__(
        self,
        handler: ObjectHandler,
        server_manager: VirtualMcpServerManager,
        descriptions: Optional[Description] = None,
    ):
        """Initialize the VmcpService.

        Args:
            handler: ObjectHandler instance for VMCP server operations.
            server_manager: VirtualMcpServerManager for managing runtime servers.
            descriptions: Optional Description instance for managing VMCP descriptions.
        """
        self.handler = handler
        self.server_manager = server_manager
        self.descriptions = descriptions

    def _resolve_uuid(self, uuid_or_name: str) -> str:
        """Resolve a VMCP server identifier to its UUID.
        
        Args:
            uuid_or_name: VMCP server UUID or name to resolve.
            
        Returns:
            str: The resolved UUID.
            
        Raises:
            KeyError: If VMCP server not found.
        """
        try:
            return self.handler.resolve_to_uuid_or_error(uuid_or_name)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"VMCP server '{uuid_or_name}' not found")
            raise

    def _resolve_skill_uuids(self, skill_uuid: Optional[str]):
        """Resolve a skill UUID to its tool and snippet UUIDs.

        Routes the lookup through the sibling :class:`SkillsService` singleton
        (obtained from
        :func:`skillberry_store.services.registry.get_service`) rather than
        the skill handler directly.

        Args:
            skill_uuid: Optional skill UUID to resolve.

        Returns:
            Tuple[List[str], List[str]]: Tool UUIDs and snippet UUIDs from the
                skill. Returns ``([], [])`` when ``skill_uuid`` is falsy or the
                skill cannot be loaded (errors are logged and swallowed to
                preserve the original best-effort contract used by
                ``create`` / ``update`` / ``start``).
        """
        from skillberry_store.services.registry import get_service

        tool_uuids: List[str] = []
        snippet_uuids: List[str] = []
        if not skill_uuid:
            return tool_uuids, snippet_uuids
        try:
            skill = get_service("skill").get(skill_uuid)
            tool_uuids = skill.get("tool_uuids", [])
            snippet_uuids = skill.get("snippet_uuids", [])
        except Exception as e:
            logger.warning(f"Error loading skill {skill_uuid}: {e}")
        return tool_uuids, snippet_uuids

    def create(self, data: Dict[str, Any], env_id: str = "") -> Dict[str, Any]:
        """Create a new virtual MCP server and start it.

        Creates a VMCP server entry, starts the runtime server process, and updates
        caches and indexes.

        Args:
            data: VMCP server metadata dictionary (name, skill_uuid, port, etc.).
            env_id: Optional environment ID for server isolation.

        Returns:
            Dict[str, Any]: The created VMCP server data with UUID, timestamps, and assigned port.

        Raises:
            ObjectAlreadyExistsError: If VMCP server with the same UUID already
                exists.
            PortConflictError: If the runtime manager rejects the port as
                unavailable / already in use.
            ValueError: For other server-creation failures.
        """
        from skillberry_store.services.exceptions import (
            ObjectAlreadyExistsError,
            PortConflictError,
        )

        create_vmcp_counter.inc()
        try:
            data["uuid"] = generate_or_validate_uuid(data.get("uuid"))
            if self.handler.object_exists(data["uuid"]):
                raise ObjectAlreadyExistsError(
                    f"VMCP server with UUID '{data['uuid']}' already exists"
                )
            now = datetime.now(timezone.utc).isoformat()
            data.setdefault("created_at", now)
            data["modified_at"] = now
            if data.get("name"):
                data["parent"] = self.handler.get_cache_parent_for_head(
                    data["uuid"], data["name"]
                )
            tool_uuids, snippet_uuids = self._resolve_skill_uuids(
                data.get("skill_uuid")
            )
            try:
                server = self.server_manager.add_server(
                    name=data.get("name") or "",
                    uuid=data["uuid"],
                    description=data.get("description") or "",
                    port=data.get("port"),
                    tools=tool_uuids,
                    snippets=snippet_uuids,
                    env_id=env_id,
                )
            except ValueError as e:
                msg = str(e).lower()
                if "port" in msg and (
                    "not available" in msg
                    or "in use" in msg
                    or "already in use" in msg
                ):
                    raise PortConflictError(str(e))
                raise
            data["port"] = server.port
            self.handler.write_dict(data["uuid"], data)
            if data.get("name"):
                self.handler.update_cache(data["uuid"], new_name=data["name"])
            if self.descriptions and data.get("description"):
                self.descriptions.write_description(data["uuid"], data["description"])
            logger.info(
                f"VMCP server '{data.get('name')}' created on port {server.port}"
            )
            return data
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error creating vmcp server '{data.get('name')}': {e}")
            raise

    def _safe_read(self, uuid: str, label: str) -> Dict[str, Any]:
        """Safely read a VMCP server dictionary with error handling.
        
        Args:
            uuid: VMCP server UUID to read.
            label: Human-readable label for error messages.
            
        Returns:
            Dict[str, Any]: VMCP server metadata dictionary.
            
        Raises:
            KeyError: If VMCP server not found.
        """
        try:
            return self.handler.read_dict(uuid)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"VMCP server '{label}' not found")
            raise

    def get(self, uuid_or_name: str) -> Dict[str, Any]:
        """Get VMCP server metadata by UUID or name with runtime status.

        Args:
            uuid_or_name: VMCP server UUID or name.

        Returns:
            Dict[str, Any]: VMCP server metadata with 'running' and 'runtime' fields.

        Raises:
            KeyError: If VMCP server not found.
        """
        get_vmcp_counter.inc()
        try:
            uuid = self._resolve_uuid(uuid_or_name)
            d = self._safe_read(uuid, uuid_or_name)
            try:
                runtime_details = self.server_manager.get_server_details(
                    d.get("name", ""), d.get("uuid", "")
                )
                d["runtime"] = runtime_details
                d["running"] = True
            except Exception:
                d["running"] = False
                d["runtime"] = None
            return d
        except KeyError:
            raise
        except Exception as e:
            logger.error(f"Error retrieving vmcp server '{uuid_or_name}': {e}")
            raise

    def list_all(self, skill_uuid: Optional[str] = None) -> Dict[str, Any]:
        """List all VMCP servers with runtime status.

        Args:
            skill_uuid: When provided, restrict the result to servers whose
                ``skill_uuid`` matches this value.

        Returns:
            Dict[str, Any]: Dictionary with 'virtual_mcp_servers' key containing server info
                           indexed by UUID, including runtime status.
        """
        list_vmcp_counter.inc()
        try:
            items = self.handler.list_all_dicts()
            if skill_uuid:
                items = [i for i in items if i.get("skill_uuid") == skill_uuid]
            servers = []
            for item in items:
                try:
                    runtime = None
                    try:
                        runtime = self.server_manager.get_server(
                            item.get("name", ""), item.get("uuid", "")
                        )
                    except Exception:
                        pass
                    info = {
                        "uuid": item.get("uuid"),
                        "name": item.get("name"),
                        "description": item.get("description"),
                        "version": item.get("version"),
                        "state": item.get("state"),
                        "tags": item.get("tags", []),
                        "port": item.get("port"),
                        "skill_uuid": item.get("skill_uuid"),
                        "modified_at": item.get("modified_at", ""),
                        "running": runtime is not None,
                        "runtime": (
                            {
                                "name": runtime.name,
                                "description": runtime.description,
                                "port": runtime.port,
                                "tools": runtime.tool_uuids,
                            }
                            if runtime
                            else None
                        ),
                    }
                    servers.append(info)
                except Exception as e:
                    logger.warning(
                        f"Error loading vmcp server '{item.get('name')}': {e}"
                    )
            servers.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
            return {"virtual_mcp_servers": {s["uuid"]: s for s in servers}}
        except Exception as e:
            logger.error(f"Error listing vmcp servers: {e}")
            raise

    def search(
        self,
        search_term: str,
        max_number_of_results: int = 5,
        similarity_threshold: float = 1.0,
        manifest_filter: str = ".",
        lifecycle_state: Optional["LifecycleState"] = None,
    ) -> List[Dict[str, Any]]:
        """Search VMCP servers by semantic similarity to a search term.

        Performs a vector-similarity search over VMCP server descriptions, then
        filters by similarity threshold, manifest properties, and lifecycle state,
        and returns matched names with similarity scores sorted by ``modified_at``
        (most recent first).

        Args:
            search_term: Free-text query to match against VMCP descriptions.
            max_number_of_results: Upper bound on candidates returned by the
                vector index before threshold filtering.
            similarity_threshold: Maximum allowed similarity score (lower is
                more similar).
            manifest_filter: Manifest property filter expression
                (e.g. ``"tags:python"``, ``"state:approved"``).
            lifecycle_state: Lifecycle state filter. Defaults to
                ``LifecycleState.ANY`` when ``None`` is passed.

        Returns:
            List[Dict[str, Any]]: Matches, each ``{"filename": <name>, "similarity_score": <float>}``.

        Raises:
            RuntimeError: If the service was constructed without a
                ``Description`` instance (search index unavailable).
        """
        from skillberry_store.modules.lifecycle import LifecycleState
        from skillberry_store.fast_api.search_filters import apply_search_filters

        search_vmcp_counter.inc()
        try:
            if lifecycle_state is None:
                lifecycle_state = LifecycleState.ANY
            if not self.descriptions:
                raise RuntimeError("VMCP server search is not available")

            matched_entities = self.descriptions.search_description(
                search_term=search_term, k=max_number_of_results
            )
            filtered = [
                m
                for m in matched_entities
                if float(m.get("similarity_score", 0)) <= similarity_threshold
            ]
            candidates: List[Dict[str, Any]] = []
            for m in filtered:
                vmcp_uuid = m.get("filename") or m.get("name")
                if not vmcp_uuid:
                    continue
                try:
                    d = self.handler.read_dict(vmcp_uuid)
                    d["similarity_score"] = m.get("similarity_score", 0.0)
                    candidates.append(d)
                except Exception as exc:
                    logger.warning(f"Could not load vmcp '{vmcp_uuid}': {exc}")
            result_items = apply_search_filters(
                candidates,
                manifest_filter=manifest_filter,
                lifecycle_state=lifecycle_state,
            )
            result_items.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
            return [
                {
                    "filename": s.get("name", ""),
                    "similarity_score": s.get("similarity_score", 0.0),
                }
                for s in result_items
                if s.get("name")
            ]
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Error searching vmcp servers: {e}")
            raise

    def update(
        self, uuid_or_name: str, data: Dict[str, Any], env_id: str = ""
    ) -> Dict[str, Any]:
        """Update an existing VMCP server's metadata and restart it.

        Stops the old runtime server, updates metadata, starts a new runtime server
        with updated configuration, and updates caches and indexes.

        Args:
            uuid_or_name: VMCP server UUID or name to update.
            data: Dictionary of fields to update.
            env_id: Optional environment ID for server isolation.

        Returns:
            Dict[str, Any]: The updated VMCP server metadata with new port.

        Raises:
            KeyError: If VMCP server not found.
        """
        update_vmcp_counter.inc()
        try:
            uuid = self._resolve_uuid(uuid_or_name)
            existing = self.handler.read_dict(uuid)
            old_name = existing.get("name")
            old_parent = existing.get("parent")
            server_uuid = existing.get("uuid")
            data["modified_at"] = datetime.now(timezone.utc).isoformat()
            if not data.get("uuid"):
                data["uuid"] = server_uuid
            new_name = data.get("name")
            if new_name:
                data["parent"] = self.handler.get_cache_parent_for_head(
                    data["uuid"] or "", new_name
                )
            try:
                self.server_manager.remove_server(old_name or "", server_uuid or "")
            except Exception as e:
                logger.warning(f"Could not stop old runtime server: {e}")
            tool_uuids, snippet_uuids = self._resolve_skill_uuids(
                data.get("skill_uuid")
            )
            server = self.server_manager.add_server(
                name=new_name or "",
                uuid=data["uuid"] or "",
                description=data.get("description") or "",
                port=data.get("port"),
                tools=tool_uuids,
                snippets=snippet_uuids,
                env_id=env_id,
            )
            data["port"] = server.port
            self.handler.write_dict(data["uuid"] or "", data)
            if new_name and old_name:
                self.handler.update_cache(
                    data["uuid"] or "",
                    new_name=new_name,
                    old_name=old_name,
                    old_parent=old_parent,
                )
            uuid_value = data.get("uuid")
            if self.descriptions and data.get("description") and uuid_value:
                self.descriptions.write_description(uuid_value, data["description"])
            logger.info(f"VMCP server '{new_name}' updated on port {server.port}")
            return data
        except KeyError:
            raise
        except Exception as e:
            logger.error(f"Error updating vmcp server '{uuid_or_name}': {e}")
            raise

    def start(
        self,
        uuid_or_name: str,
        env_id: str = "",
    ) -> Tuple[Any, bool]:
        """Start (or report already-running) a VMCP server runtime.

        Resolves the VMCP server, checks whether its runtime is already up; if
        so, returns the existing runtime with ``already_running=True``. Otherwise
        resolves the associated skill's tools and snippets and adds the server
        via the runtime manager.

        Args:
            uuid_or_name: VMCP server UUID or name to start.
            env_id: Optional environment ID for runtime isolation.

        Returns:
            Tuple[Any, bool]: Pair of the runtime server object (whose ``.port``
                and ``.name`` callers may read) and a boolean that is ``True``
                when the server was already running and ``False`` when it was
                started by this call.

        Raises:
            KeyError: If the VMCP server is not found.
        """
        start_vmcp_counter.inc()
        try:
            vmcp_uuid = self._resolve_uuid(uuid_or_name)
            vmcp_data = self.handler.read_dict(vmcp_uuid)
            server_name = vmcp_data.get("name", "")
            server_uuid = vmcp_data.get("uuid", "")
            try:
                existing = self.server_manager.get_server(server_name, server_uuid)
                if existing:
                    return existing, True
            except Exception:
                pass
            tool_uuids, snippet_uuids = self._resolve_skill_uuids(
                vmcp_data.get("skill_uuid")
            )
            server = self.server_manager.add_server(
                name=server_name,
                uuid=server_uuid,
                description=vmcp_data.get("description", ""),
                port=vmcp_data.get("port"),
                tools=tool_uuids,
                snippets=snippet_uuids,
                env_id=env_id,
            )
            logger.info(f"VMCP server '{server_name}' started on port {server.port}")
            return server, False
        except (KeyError, ValueError):
            raise
        except Exception as e:
            logger.error(f"Error starting vmcp server '{uuid_or_name}': {e}")
            raise

    def delete(self, uuid_or_name: str) -> None:
        """Delete a VMCP server and stop its runtime process.

        Stops the runtime server, removes metadata, cache entries, and description indexes.

        Args:
            uuid_or_name: VMCP server UUID or name to delete.

        Raises:
            KeyError: If VMCP server not found.
        """
        delete_vmcp_counter.inc()
        try:
            uuid = self._resolve_uuid(uuid_or_name)
            d = self.handler.read_dict(uuid)
            name = d.get("name")
            parent = d.get("parent")
            try:
                self.server_manager.remove_server(name or "", uuid or "")
            except Exception as e:
                logger.warning(f"Could not stop runtime server: {e}")
            if name and uuid:
                self.handler.update_cache(
                    uuid, new_name=None, old_name=name, old_parent=parent
                )
            self.handler.delete_object(uuid)
            if self.descriptions:
                try:
                    self.descriptions.delete_description(uuid)
                except Exception as e:
                    logger.warning(
                        f"Could not delete vmcp description for {uuid}: {e}"
                    )
            logger.info(f"VMCP server '{uuid_or_name}' deleted")
        except KeyError:
            raise
        except Exception as e:
            logger.error(f"Error deleting vmcp server '{uuid_or_name}': {e}")
            raise

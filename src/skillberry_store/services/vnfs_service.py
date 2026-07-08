"""Business logic for virtual NFS server CRUD operations."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from prometheus_client import Counter

from skillberry_store.modules.object_handler import ObjectHandler
from skillberry_store.utils.utils import generate_or_validate_uuid

if TYPE_CHECKING:
    from skillberry_store.modules.lifecycle import LifecycleState
    from skillberry_store.modules.vnfs_server_manager import VirtualNfsServerManager

logger = logging.getLogger(__name__)

# observability - metrics
prom_prefix = "sts_service_vnfs_"
create_vnfs_counter = Counter(f"{prom_prefix}create_counter", "vNFS create operations")
list_vnfs_counter = Counter(f"{prom_prefix}list_counter", "vNFS list operations")
get_vnfs_counter = Counter(f"{prom_prefix}get_counter", "vNFS get operations")
delete_vnfs_counter = Counter(f"{prom_prefix}delete_counter", "vNFS delete operations")
update_vnfs_counter = Counter(f"{prom_prefix}update_counter", "vNFS update operations")
start_vnfs_counter = Counter(f"{prom_prefix}start_counter", "vNFS start operations")
search_vnfs_counter = Counter(f"{prom_prefix}search_counter", "vNFS search operations")


def _to_ns(data: Dict[str, Any]) -> SimpleNamespace:
    """Build a SimpleNamespace with attributes needed by VirtualNfsServerManager.add_server.

    Args:
        data: Dictionary containing vNFS server configuration.

    Returns:
        SimpleNamespace: Object with name, uuid, port, skill_uuid, description,
        protocol, and npx_compat attributes.
    """
    return SimpleNamespace(
        name=data.get("name"),
        uuid=data.get("uuid"),
        port=data.get("port"),
        skill_uuid=data.get("skill_uuid"),
        description=data.get("description") or "",
        protocol=data.get("protocol", "webdav"),
        npx_compat=bool(data.get("npx_compat", False)),
    )


def _compute_install_url(data: Dict[str, Any], request_host: Optional[str] = None) -> Optional[str]:
    """Return the ``npx skills add`` URL for a vNFS, or None when not applicable.

    Only vNFS servers with ``protocol == "webdav"`` and ``npx_compat == True``
    have an install URL. The host is resolved with the following precedence:

    1. ``SBS_VNFS_PUBLIC_HOST`` env var (deployment override).
    2. The ``Host`` header from the current request (when provided).
    3. ``localhost`` as a safe local default.

    Args:
        data: vNFS server dict with at least ``port`` and ``protocol``.
        request_host: Optional value of the request ``Host`` header
            (already stripped of any port suffix).

    Returns:
        The install URL string, or None when the vNFS is not eligible.
    """
    import os

    if data.get("protocol") != "webdav" or not data.get("npx_compat"):
        return None
    port = data.get("port")
    if not port:
        return None
    host = (
        os.environ.get("SBS_VNFS_PUBLIC_HOST")
        or request_host
        or "localhost"
    )
    return f"http://{host}:{port}"


class VnfsService:
    """Service layer for virtual NFS server CRUD operations.
    
    Provides business logic for managing virtual NFS servers, which expose
    snippets through network file system interfaces on specified ports.
    
    Attributes:
        handler: ObjectHandler for vNFS server persistence operations.
        server_manager: VirtualNfsServerManager for runtime server management.
        descriptions: accessed via ``handler.descriptions`` (not stored as a separate attribute).
    """
    
    def __init__(
        self,
        handler: ObjectHandler,
        server_manager: VirtualNfsServerManager,
    ):
        """Initialize the VnfsService.
        
        Args:
            handler: ObjectHandler instance for vNFS server operations.
            server_manager: VirtualNfsServerManager for managing runtime servers.
        """
        self.handler = handler
        self.server_manager = server_manager


    def _enforce_slug_for_referenced_skill(self, skill_uuid: str) -> None:
        """Reject if the referenced skill's name is not a valid npx slug.

        Called on create/update when ``npx_compat`` is set. Raises
        :class:`ValueError` with an actionable message including the suggested
        slug so the FastAPI layer can render a 400.
        """
        from skillberry_store.tools.anthropic.naming import validate_skill_slug
        from skillberry_store.modules.object_handler import get_object_handler

        try:
            skill_dict = get_object_handler("skill").read_dict(skill_uuid)
        except Exception as exc:  # pragma: no cover - defensive
            raise ValueError(
                f"Cannot enable npx_compat: referenced skill "
                f"'{skill_uuid}' could not be read ({exc})."
            )
        name = skill_dict.get("name")
        result = validate_skill_slug(name)
        if not result.ok:
            raise ValueError(
                f"npx_compat requires a slug-safe skill name. "
                f"Skill '{name}' is invalid: {result.reason} "
                f"Rename to '{result.suggested}' and try again."
            )

    def _resolve_uuid(self, uuid_or_name: str) -> str:
        """Resolve a vNFS server identifier to its UUID.
        
        Args:
            uuid_or_name: vNFS server UUID or name to resolve.
            
        Returns:
            str: The resolved UUID.
            
        Raises:
            KeyError: If vNFS server not found.
        """
        try:
            return self.handler.resolve_to_uuid_or_error(uuid_or_name)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"vNFS server '{uuid_or_name}' not found")
            raise

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new virtual NFS server and start it.

        Creates a vNFS server entry, starts the runtime server process, and updates
        caches and indexes.

        Args:
            data: vNFS server metadata dictionary (name, skill_uuid, port, protocol, etc.).

        Returns:
            Dict[str, Any]: The created vNFS server data with UUID, timestamps, and assigned port.

        Raises:
            ObjectAlreadyExistsError: If vNFS server with the same UUID already exists.
            PortConflictError: If the runtime manager rejects the port as
                unavailable / already in use.
            ValueError: For other server-creation failures.
        """
        from skillberry_store.services.exceptions import (
            ObjectAlreadyExistsError,
            PortConflictError,
        )

        create_vnfs_counter.inc()
        try:
            data["uuid"] = generate_or_validate_uuid(data.get("uuid"))
            if self.handler.object_exists(data["uuid"]):
                raise ObjectAlreadyExistsError(
                    f"vNFS server with UUID '{data['uuid']}' already exists"
                )
            now = datetime.now(timezone.utc).isoformat()
            data.setdefault("created_at", now)
            data["modified_at"] = now
            if data.get("name"):
                data["parent"] = self.handler.get_cache_parent_for_head(
                    data["uuid"], data["name"]
                )
            if data.get("npx_compat") and data.get("skill_uuid"):
                # Pre-flight: refuse to boot an npx-compat vNFS whose skill
                # name is not slug-safe. Raising here surfaces a clean 400
                # with a suggested slug instead of a generic 500 from the
                # exporter later in add_server().
                self._enforce_slug_for_referenced_skill(data["skill_uuid"])
            try:
                server = self.server_manager.add_server(_to_ns(data))
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
            if data.get("skill_uuid"):
                from skillberry_store.services.registry import get_service
                get_service("skill").add_dependent("vnfs", data["uuid"], [data["skill_uuid"]])
            if data.get("name"):
                self.handler.update_cache(data["uuid"], new_name=data["name"])
            if self.handler.descriptions and data.get("description"):
                self.handler.descriptions.write_description(data["uuid"], data["description"])
            logger.info(
                f"vNFS server '{data.get('name')}' created on port {server.port}"
            )
            return data
        except ValueError:
            raise
        except Exception as exc:
            logger.error(f"Error creating vnfs server '{data.get('name')}': {exc}")
            raise

    def _safe_read(self, uuid: str, label: str) -> Dict[str, Any]:
        """Safely read a vNFS server dictionary with error handling.
        
        Args:
            uuid: vNFS server UUID to read.
            label: Human-readable label for error messages.
            
        Returns:
            Dict[str, Any]: vNFS server metadata dictionary.
            
        Raises:
            KeyError: If vNFS server not found.
        """
        try:
            return self.handler.read_dict(uuid)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"vNFS server '{label}' not found")
            raise

    def get(self, uuid_or_name: str) -> Dict[str, Any]:
        """Get vNFS server metadata by UUID or name with runtime status.

        Args:
            uuid_or_name: vNFS server UUID or name.

        Returns:
            Dict[str, Any]: vNFS server metadata with 'running' and 'export_path' fields.

        Raises:
            KeyError: If vNFS server not found.
        """
        get_vnfs_counter.inc()
        try:
            uuid = self._resolve_uuid(uuid_or_name)
            with self.handler.read_lock(uuid):
                d = self._safe_read(uuid, uuid_or_name)
                try:
                    runtime = self.server_manager.get_server(
                        d.get("name", ""), d.get("uuid", "")
                    )
                    d["running"] = runtime is not None and runtime.running
                    d["export_path"] = str(runtime.export_path) if runtime else None
                    if runtime is not None:
                        d["npx_compat"] = getattr(runtime, "npx_compat", d.get("npx_compat", False))
                except Exception:
                    d["running"] = False
                    d["export_path"] = None
                d.setdefault("npx_compat", False)
                d["install_url"] = _compute_install_url(d)
                return d
        except KeyError:
            raise
        except Exception as exc:
            logger.error(f"Error retrieving vnfs server '{uuid_or_name}': {exc}")
            raise

    def list_all(self, skill_uuid: Optional[str] = None) -> Dict[str, Any]:
        """List all vNFS servers with runtime status.

        Args:
            skill_uuid: When provided, restrict the result to servers whose
                ``skill_uuid`` matches this value.

        Returns:
            Dict[str, Any]: Dictionary with 'virtual_nfs_servers' key containing server info
                           indexed by UUID, including runtime status and export paths.
        """
        list_vnfs_counter.inc()
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
                        "protocol": item.get("protocol", "webdav"),
                        "npx_compat": bool(item.get("npx_compat", False)),
                        "modified_at": item.get("modified_at", ""),
                        "running": runtime is not None and runtime.running,
                        "export_path": str(runtime.export_path) if runtime else None,
                    }
                    info["install_url"] = _compute_install_url(info)
                    servers.append(info)
                except Exception as e:
                    logger.warning(
                        f"Error loading vnfs server '{item.get('name')}': {e}"
                    )
            servers.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
            return {"virtual_nfs_servers": {s["uuid"]: s for s in servers}}
        except Exception as exc:
            logger.error(f"Error listing vnfs servers: {exc}")
            raise

    def search(
        self,
        search_term: str,
        max_number_of_results: int = 5,
        similarity_threshold: float = 1.0,
        manifest_filter: str = ".",
        lifecycle_state: Optional["LifecycleState"] = None,
    ) -> List[Dict[str, Any]]:
        """Search vNFS servers by semantic similarity to a search term.

        Performs a vector-similarity search over vNFS server descriptions, then
        filters by similarity threshold, manifest properties, and lifecycle state,
        and returns matched names with similarity scores sorted by ``modified_at``
        (most recent first).

        Args:
            search_term: Free-text query to match against vNFS descriptions.
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

        search_vnfs_counter.inc()
        try:
            if lifecycle_state is None:
                lifecycle_state = LifecycleState.ANY
            if not self.handler.descriptions:
                raise RuntimeError("vNFS server search is not available")

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
                vnfs_uuid = m.get("filename") or m.get("name")
                if not vnfs_uuid:
                    continue
                try:
                    d = self.handler.read_dict(vnfs_uuid)
                    d["similarity_score"] = m.get("similarity_score", 0.0)
                    candidates.append(d)
                except Exception as exc:
                    logger.warning(f"Could not load vnfs '{vnfs_uuid}': {exc}")
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
        except Exception as exc:
            logger.error(f"Error searching vnfs servers: {exc}")
            raise

    def update(self, uuid_or_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing vNFS server's metadata and restart it.

        Stops the old runtime server, updates metadata, starts a new runtime server
        with updated configuration, and updates caches and indexes.

        Args:
            uuid_or_name: vNFS server UUID or name to update.
            data: Dictionary of fields to update.

        Returns:
            Dict[str, Any]: The updated vNFS server metadata with new port.

        Raises:
            KeyError: If vNFS server not found.
        """
        update_vnfs_counter.inc()
        try:
            uuid = self._resolve_uuid(uuid_or_name)
            with self.handler.write_lock(uuid):
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
                if data.get("npx_compat") and data.get("skill_uuid"):
                    self._enforce_slug_for_referenced_skill(data["skill_uuid"])
                try:
                    self.server_manager.remove_server(old_name or "", server_uuid or "")
                except Exception as e:
                    logger.warning(f"Could not stop old runtime server: {e}")
                server = self.server_manager.add_server(_to_ns(data))
                data["port"] = server.port
                from skillberry_store.services.registry import get_service
                get_service("skill").remove_dependent("vnfs", uuid)
                self.handler.write_dict(data["uuid"] or "", data)
                if data.get("skill_uuid"):
                    get_service("skill").add_dependent(
                        "vnfs", data["uuid"] or uuid, [data["skill_uuid"]]
                    )
                if new_name and old_name:
                    self.handler.update_cache(
                        data["uuid"] or "",
                        new_name=new_name,
                        old_name=old_name,
                        old_parent=old_parent,
                    )
                uuid_value = data.get("uuid")
                if self.handler.descriptions and data.get("description") and uuid_value:
                    self.handler.descriptions.write_description(uuid_value, data["description"])
                logger.info(f"vNFS server '{new_name}' updated on port {server.port}")
                return data
        except KeyError:
            raise
        except Exception as exc:
            logger.error(f"Error updating vnfs server '{uuid_or_name}': {exc}")
            raise

    def start(self, uuid_or_name: str) -> Tuple[Any, bool]:
        """Start (or report already-running) a vNFS server runtime.

        Resolves the vNFS server, checks whether its runtime is already up and
        running; if so, returns the existing runtime with
        ``already_running=True``. Otherwise adds the server via the runtime
        manager.

        Args:
            uuid_or_name: vNFS server UUID or name to start.

        Returns:
            Tuple[Any, bool]: Pair of the runtime server object (whose ``.port``
                callers may read) and a boolean that is ``True`` when the server
                was already running and ``False`` when it was started by this
                call.

        Raises:
            KeyError: If the vNFS server is not found.
        """
        start_vnfs_counter.inc()
        try:
            vnfs_uuid = self._resolve_uuid(uuid_or_name)
            with self.handler.write_lock(vnfs_uuid):
                vnfs_data = self.handler.read_dict(vnfs_uuid)
                server_name = vnfs_data.get("name", "")
                server_uuid = vnfs_data.get("uuid", "")
                try:
                    existing = self.server_manager.get_server(server_name, server_uuid)
                    if existing and existing.running:
                        return existing, True
                except Exception:
                    pass
                server = self.server_manager.add_server(_to_ns(vnfs_data))
                logger.info(f"vNFS server '{server_name}' started on port {server.port}")
                return server, False
        except (KeyError, ValueError):
            raise
        except Exception as exc:
            logger.error(f"Error starting vnfs server '{uuid_or_name}': {exc}")
            raise

    def delete(self, uuid_or_name: str) -> None:
        """Delete a vNFS server and stop its runtime process.

        Stops the runtime server, removes metadata, cache entries, and description indexes.

        Args:
            uuid_or_name: vNFS server UUID or name to delete.

        Raises:
            KeyError: If vNFS server not found.
        """
        delete_vnfs_counter.inc()
        try:
            uuid = self._resolve_uuid(uuid_or_name)
            with self.handler.write_lock(uuid):
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
                from skillberry_store.services.registry import get_service
                get_service("skill").remove_dependent("vnfs", uuid)
                if self.handler.descriptions:
                    try:
                        self.handler.descriptions.delete_description(uuid)
                    except Exception as e:
                        logger.warning(
                            f"Could not delete vnfs description for {uuid}: {e}"
                        )
                logger.info(f"vNFS server '{uuid_or_name}' deleted")
        except KeyError:
            raise
        except Exception as exc:
            logger.error(f"Error deleting vnfs server '{uuid_or_name}': {exc}")
            raise

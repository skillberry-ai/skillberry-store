"""Business logic for tool CRUD and execution operations."""

from __future__ import annotations

import logging
import time
import traceback
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from prometheus_client import Counter, Histogram

from skillberry_store.modules.object_handler import ObjectHandler
from skillberry_store.modules.file_executor import detect_tool_dependencies
from skillberry_store.plugins.events import (
    emit_content_added,
    emit_content_deleted,
    emit_content_updated,
)
from skillberry_store.services.exceptions import ObjectAlreadyExistsError, ObjectInUseError
from skillberry_store.utils.utils import generate_or_validate_uuid
from skillberry_store.tools.configure import is_auto_detect_dependencies_enabled

if TYPE_CHECKING:
    from skillberry_store.modules.lifecycle import LifecycleState

logger = logging.getLogger(__name__)

# observability - metrics
prom_prefix = "sts_service_tools_"
create_tool_counter = Counter(
    f"{prom_prefix}create_tool_counter", "Count number of tool create operations"
)
list_tools_counter = Counter(
    f"{prom_prefix}list_tools_counter", "Count number of tool list operations"
)
get_tool_counter = Counter(
    f"{prom_prefix}get_tool_counter", "Count number of tool get operations"
)
get_tool_module_counter = Counter(
    f"{prom_prefix}get_tool_module_counter",
    "Count number of tool module get operations",
)
delete_tool_counter = Counter(
    f"{prom_prefix}delete_tool_counter", "Count number of tool delete operations"
)
update_tool_counter = Counter(
    f"{prom_prefix}update_tool_counter", "Count number of tool update operations"
)
execute_tool_counter = Counter(
    f"{prom_prefix}execute_tool_counter",
    "Count number of tool execute operations",
    ["name"],
)
execute_successfully_tool_counter = Counter(
    f"{prom_prefix}execute_successfully_tool_counter",
    "Count number of tool executed successfully operations",
    ["name"],
)
execute_successfully_tool_latency = Histogram(
    f"{prom_prefix}execute_successfully_tool_latency",
    "Histogram of execute tool successfully latencies",
    ["name"],
)
search_tools_counter = Counter(
    f"{prom_prefix}search_tools_counter", "Count number of tool search operations"
)
add_tool_from_python_counter = Counter(
    f"{prom_prefix}add_tool_from_python_counter",
    "Count number of tool add from Python operations",
)


class ToolsService:
    """Service layer for tool CRUD and execution operations.
    
    Provides business logic for managing tools including creation, retrieval,
    update, deletion, and dependency resolution. Handles both tool metadata
    and module files.
    
    Attributes:
        handler: ObjectHandler for tool persistence operations.
        descriptions: accessed via ``handler.descriptions`` (not stored as a separate attribute).
    """
    
    def __init__(self, handler: ObjectHandler):
        """Initialize the ToolsService.
        
        Args:
            handler: ObjectHandler instance for tool operations.
        """
        self.handler = handler


    def _resolve_uuid(self, uuid_or_name: str) -> str:
        """Resolve a tool identifier to its UUID.
        
        Args:
            uuid_or_name: Tool UUID or name to resolve.
            
        Returns:
            str: The resolved UUID.
            
        Raises:
            KeyError: If tool not found.
        """
        try:
            return self.handler.resolve_to_uuid_or_error(uuid_or_name)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"Tool '{uuid_or_name}' not found")
            raise

    def add_dependent(
        self, referencing_type: str, referencing_uuid: str, referenced_tool_uuids: List[str]
    ) -> None:
        """Register that ``referencing_uuid`` depends on each UUID in ``referenced_tool_uuids``.

        Called by sibling services (e.g. ``SkillsService``) when they create or
        update an object that references tools.  Also called by this service for
        tool-on-tool ``dependencies`` fields.

        Args:
            referencing_type: Object type of the referencing object (e.g. ``"skill"``).
            referencing_uuid: UUID of the referencing object.
            referenced_tool_uuids: UUIDs of the tools being depended on.
        """
        self.handler.dependency_manager.add(
            referencing_type, referencing_uuid, referenced_tool_uuids
        )

    def remove_dependent(self, referencing_type: str, referencing_uuid: str) -> None:
        """Remove all dependency records where ``referencing_uuid`` is the referencing side.

        Called when the referencing object is updated (to re-register with new refs)
        or deleted (to clean up).

        Args:
            referencing_type: Object type of the referencing object.
            referencing_uuid: UUID of the referencing object.
        """
        self.handler.dependency_manager.remove_referencing(referencing_type, referencing_uuid)

    def find_dependencies(self, dependencies: List[str], tool_uuid: str) -> Set[str]:
        """Recursively resolve all transitive dependency UUIDs.

        Traverses the dependency tree to find all direct and indirect dependencies
        of a tool, avoiding circular dependencies.

        Args:
            dependencies: List of direct dependency UUIDs.
            tool_uuid: UUID of the tool being analyzed (for logging).

        Returns:
            Set[str]: Set of all dependency UUIDs (transitive closure).
        """
        found: Set[str] = set()
        if not dependencies:
            return found
        for dep_uuid in dependencies:
            if dep_uuid in found:
                continue
            found.add(dep_uuid)
            dep_dict = self.handler.read_dict(dep_uuid)
            nested = dep_dict.get("dependencies", [])
            if nested:
                found.update(self.find_dependencies(nested, dep_uuid))
        return found

    async def execute(
        self,
        uuid_or_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        env_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a tool by UUID or name.

        Resolves the tool, loads its module (or generates an MCP stub), gathers
        the transitive closure of its dependencies and their files, and runs
        the tool through a ``FileExecutor``. Returns the execution output.

        Args:
            uuid_or_name: Tool UUID or name to execute.
            parameters: Dictionary of parameters to pass to the tool. Defaults
                to an empty dictionary if ``None``.
            env_id: Optional environment ID for tool execution isolation.

        Returns:
            Dict[str, Any]: Tool execution output.

        Raises:
            KeyError: If the tool is not found, or the executor reports a
                "not found" style error.
            RuntimeError: If the executor reports any other error.
        """
        from skillberry_store.fast_api.server_utils import mcp_content_from_manifest
        from skillberry_store.modules.file_executor import FileExecutor

        uuid = self._resolve_uuid(uuid_or_name)
        with self.handler.read_lock(uuid):
            tool_dict = self._safe_read(uuid, uuid_or_name)
            tool_uuid = tool_dict["uuid"]
            tool_name = tool_dict.get("name", uuid_or_name)
            if tool_dict.get("packaging_format") == "mcp":
                module_content = mcp_content_from_manifest(tool_dict)
            else:
                module_name = tool_dict.get("module_name")
                if not module_name:
                    raise KeyError(f"Tool '{uuid_or_name}' has no module file")
                module_content = self.handler.read_file(uuid, module_name, raw_content=True)
                if not isinstance(module_content, str):
                    raise RuntimeError(
                        f"Invalid module content type for tool '{uuid_or_name}'"
                    )
            dep_uuids = self.find_dependencies(
                tool_dict.get("dependencies", []), tool_uuid
            )
            dep_dicts = self.handler.read_dicts(list(dep_uuids))
            dep_files = [
                self.handler.read_file(m["uuid"], m["module_name"], raw_content=True)
                for m in dep_dicts
            ]
        execute_tool_counter.labels(name=tool_uuid).inc()
        try:
            file_executor = FileExecutor(
                name=tool_name,
                file_content=module_content,
                file_manifest=tool_dict,
                dependent_file_contents=dep_files,
                dependent_tools_as_dict=dep_dicts,
            )
            start_time = time.time()
            result = await file_executor.execute_file(
                parameters=parameters or {}, env_id=env_id
            )
            duration = time.time() - start_time
            if isinstance(result, dict) and "error" in result:
                error_message = result.get("error", "Unknown Error")
                if "not found" in error_message.lower():
                    raise KeyError(error_message)
                raise RuntimeError(error_message)
            execute_successfully_tool_counter.labels(name=tool_uuid).inc()
            execute_successfully_tool_latency.labels(name=tool_uuid).observe(duration)
            logger.info(
                f"Tool '{tool_name}' (UUID: {tool_uuid}) executed successfully"
            )
            return result
        except (KeyError, RuntimeError):
            raise
        except Exception as e:
            logger.error(f"Error executing tool '{uuid_or_name}': {e}")
            raise

    def create(
        self,
        data: Dict[str, Any],
        module_content: bytes,
        module_filename: str,
        extra_name_to_uuid: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create a new tool with its module file.

        Creates a tool entry with metadata and saves the associated module file.
        Automatically detects dependencies if enabled and updates caches and
        indexes.

        Args:
            data: Tool metadata dictionary (name, description, params, etc.).
                If ``data`` already has ``dependencies``, auto-detection is
                skipped.
            module_content: Binary content of the tool's module file.
            module_filename: Filename for the module (e.g., "tool.py").
            extra_name_to_uuid: Optional name->UUID map of tools that aren't
                yet in the handler but should be considered "available" by
                dependency auto-detection. Used by batch imports (e.g.
                ``SkillsService.import_anthropic``) so one tool can declare a
                dependency on another tool being created in the same batch.
                When a detected dep name is in this map, its UUID is taken
                from the map; otherwise the handler resolves it.

        Returns:
            Dict[str, Any]: The created tool data with UUID and timestamps.

        Raises:
            ObjectAlreadyExistsError: If tool with the same UUID already exists.
        """
        create_tool_counter.inc()
        try:
            data["uuid"] = generate_or_validate_uuid(data.get("uuid"))
            if self.handler.object_exists(data["uuid"]):
                raise ObjectAlreadyExistsError(
                    f"Tool with UUID '{data['uuid']}' already exists"
                )
            now = datetime.now(timezone.utc).isoformat()
            data.setdefault("created_at", now)
            data["modified_at"] = now
            if data.get("name"):
                data["parent"] = self.handler.get_cache_parent_for_head(
                    data["uuid"], data["name"]
                )
            self.handler.write_file(data["uuid"], module_filename, module_content)
            data["module_name"] = module_filename
            if not data.get("dependencies") and is_auto_detect_dependencies_enabled():
                try:
                    content_str = (
                        module_content.decode("utf-8")
                        if isinstance(module_content, bytes)
                        else module_content
                    )
                    available = self.handler.get_existing_names()
                    if extra_name_to_uuid:
                        available = available | set(extra_name_to_uuid.keys())
                    detected_names = detect_tool_dependencies(
                        content_str, data["name"], available
                    )
                    if detected_names:
                        data["dependencies"] = [
                            extra_name_to_uuid[n]
                            if extra_name_to_uuid and n in extra_name_to_uuid
                            else self.handler.name_to_uuid(n)
                            for n in detected_names
                        ]
                except Exception as e:
                    logger.warning(f"Failed to auto-detect dependencies: {e}")
            self.handler.write_dict(data["uuid"], data)
            self.add_dependent("tool", data["uuid"], data.get("dependencies") or [])
            self.handler.update_cache(data["uuid"], new_name=data["name"])
            if self.handler.descriptions and data.get("description"):
                self.handler.descriptions.write_description(data["uuid"], data["description"])
            emit_content_added("tool", data["uuid"])
            logger.info(f"Tool '{data.get('name')}' created with UUID {data['uuid']}")
            return data
        except ObjectAlreadyExistsError:
            raise
        except Exception as e:
            logger.error(f"Error creating tool '{data.get('name')}': {e}")
            raise

    def _safe_read(self, uuid: str, label: str) -> Dict[str, Any]:
        """Safely read a tool dictionary with error handling.
        
        Args:
            uuid: Tool UUID to read.
            label: Human-readable label for error messages.
            
        Returns:
            Dict[str, Any]: Tool metadata dictionary.
            
        Raises:
            KeyError: If tool not found.
        """
        try:
            return self.handler.read_dict(uuid)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"Tool '{label}' not found")
            raise

    def get(
        self,
        uuid_or_name: str,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get tool metadata by UUID or name.

        Args:
            uuid_or_name: Tool UUID or name.
            fields: Optional field-selection spec (``None`` /
                ``"narrow"`` / ``"wide"`` / ``"full"`` / CSV
                allowlist). ``None`` and ``"narrow"`` both resolve to
                the narrow preset (the default). See
                :mod:`skillberry_store.services.field_selection`.

        Returns:
            Dict[str, Any]: Tool metadata dictionary, field-selected
                according to ``fields``.

        Raises:
            KeyError: If tool not found.
        """
        from skillberry_store.services.field_selection import (
            parse_fields_spec,
            select_item_fields,
        )

        get_tool_counter.inc()
        try:
            allow = parse_fields_spec(fields, "tool")
            uuid = self._resolve_uuid(uuid_or_name)
            with self.handler.read_lock(uuid):
                item = self._safe_read(uuid, uuid_or_name)
                return select_item_fields(item, allow)
        except KeyError:
            raise
        except Exception as e:
            logger.error(f"Error retrieving tool '{uuid_or_name}': {e}")
            raise

    def get_module(self, uuid_or_name: str) -> str:
        """Get the module file content for a tool.

        For code-packaged tools, returns the module's source file content.
        For MCP-packaged tools, returns a stub generated from the cached
        manifest (no MCP round-trip required).

        Args:
            uuid_or_name: Tool UUID or name.

        Returns:
            str: Module content (source code for code tools, MCP stub for MCP tools).

        Raises:
            KeyError: If tool not found, or if a code tool has no module file.
            RuntimeError: If module content type is invalid.
        """
        from skillberry_store.fast_api.server_utils import mcp_content_from_manifest

        get_tool_module_counter.inc()
        try:
            uuid = self._resolve_uuid(uuid_or_name)
            with self.handler.read_lock(uuid):
                tool = self.handler.read_dict(uuid)
                if tool.get("packaging_format") == "mcp":
                    return mcp_content_from_manifest(tool)
                module_name = tool.get("module_name")
                if not module_name:
                    raise KeyError(f"Tool '{uuid_or_name}' has no module file")
                content = self.handler.read_file(uuid, module_name, raw_content=True)
                if not isinstance(content, str):
                    raise RuntimeError(
                        f"Invalid module content type for tool '{uuid_or_name}'"
                    )
                return content
        except (KeyError, RuntimeError):
            raise
        except Exception as e:
            logger.error(f"Error retrieving module for '{uuid_or_name}': {e}")
            raise

    def list_all(
        self,
        filters: Optional[Dict] = None,
        fields: Optional[str] = None,
        search: Optional[str] = None,
        tags: Optional[List[str]] = None,
        state: Optional[str] = None,
        sort: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Any:
        """List tools with optional filter / sort / paginate / project.

        See :meth:`SnippetsService.list_all` for parameter semantics.
        Response shape follows the same convention: bare list unless
        ``limit`` or ``offset`` is provided, in which case it becomes an
        ``{items, total, offset, limit}`` envelope.
        """
        from skillberry_store.services.field_selection import (
            parse_fields_spec,
            select_items_fields,
        )
        from skillberry_store.services.list_query import (
            apply_filters,
            apply_pagination,
            apply_sort,
            is_paginated,
        )

        list_tools_counter.inc()
        try:
            items = self.handler.list_all_dicts()
            if filters:
                items = [
                    i for i in items if all(i.get(k) == v for k, v in filters.items())
                ]
            items = apply_filters(items, search=search, tags=tags, state=state)
            items = apply_sort(items, sort)
            page, total = apply_pagination(items, limit, offset)
            allow = parse_fields_spec(fields, "tool")
            projected = select_items_fields(page, allow)
            if not is_paginated(limit, offset):
                return projected
            return {
                "items": projected,
                "total": total,
                "offset": offset or 0,
                "limit": limit,
            }
        except Exception as e:
            logger.error(f"Error listing tools: {e}\n{traceback.format_exc()}")
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
        """Search tools by semantic similarity to a search term.

        Performs a vector-similarity search over tool descriptions, then filters
        by similarity threshold, manifest properties, and lifecycle state, and
        returns matched names with similarity scores sorted by ``modified_at``
        (most recent first).

        Args:
            search_term: Free-text query to match against tool descriptions.
            max_number_of_results: Upper bound on candidates returned by the
                vector index before threshold filtering.
            similarity_threshold: Maximum allowed similarity score (lower is
                more similar). Candidates above this score are discarded.
            manifest_filter: Manifest property filter expression
                (e.g. ``"tags:python"``, ``"state:approved"``). ``"."`` matches
                all entities.
            lifecycle_state: Lifecycle state filter. Defaults to
                ``LifecycleState.ANY`` when ``None`` is passed.
            fields: Optional field-selection spec — same grammar as
                :meth:`list_all` (``None`` / ``"narrow"`` / ``"wide"``
                / ``"full"`` / CSV allowlist). Each match is a
                field-selected tool dict with ``similarity_score``
                merged in. Default (``None``) resolves to ``"narrow"``
                — the minimal UI listing set.

        Returns:
            List[Dict[str, Any]]: Matches sorted by ``modified_at`` desc.
                Each entry is a field-selected tool dict plus a
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

        search_tools_counter.inc()
        try:
            if lifecycle_state is None:
                lifecycle_state = LifecycleState.ANY
            if not self.handler.descriptions:
                raise RuntimeError(
                    "Tool search is not available - descriptions not initialized"
                )

            matched_entities = self.handler.descriptions.search_description(
                search_term=search_term, k=max_number_of_results
            )
            filtered_matched = [
                m
                for m in matched_entities
                if float(m["similarity_score"]) <= similarity_threshold
            ]
            candidates: List[Dict[str, Any]] = []
            for matched in filtered_matched:
                tool_name = matched.get("filename") or matched.get("name")
                if not tool_name:
                    continue
                try:
                    fetched = self.get(tool_name, fields="full")
                    candidate = dict(fetched)
                    candidate["similarity_score"] = matched.get(
                        "similarity_score", 0.0
                    )
                    candidates.append(candidate)
                except Exception as e:
                    logger.warning(f"Could not load tool {tool_name}: {e}")
            filtered_tools = apply_search_filters(
                candidates,
                manifest_filter=manifest_filter,
                lifecycle_state=lifecycle_state,
            )
            filtered_tools.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
            allow = parse_fields_spec(fields, "tool")
            return [
                {
                    **select_item_fields(t, allow),
                    "similarity_score": t.get("similarity_score", 0.0),
                }
                for t in filtered_tools
                if t.get("name")
            ]
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Error searching tools: {e}")
            raise

    def update(self, uuid_or_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing tool's metadata.

        Merges new data with existing tool data, updates timestamps, caches,
        and description indexes as needed.

        Args:
            uuid_or_name: Tool UUID or name to update.
            data: Dictionary of fields to update.

        Returns:
            Dict[str, Any]: The updated tool metadata.

        Raises:
            KeyError: If tool not found.
        """
        update_tool_counter.inc()
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
                self.remove_dependent("tool", uuid)
                self.handler.write_dict(uuid, merged)
                self.add_dependent("tool", uuid, merged.get("dependencies") or [])
                if new_name:
                    self.handler.update_cache(
                        uuid, new_name=new_name, old_name=old_name, old_parent=old_parent
                    )
                if self.handler.descriptions and data.get("description"):
                    old_desc = existing.get("description")
                    if old_desc != data["description"]:
                        try:
                            self.handler.descriptions.delete_description(uuid)
                        except Exception:
                            pass
                        self.handler.descriptions.write_description(uuid, data["description"])
                emit_content_updated("tool", uuid)
                logger.info(f"Tool '{uuid_or_name}' updated")
                return merged
        except KeyError:
            raise
        except Exception as e:
            logger.error(f"Error updating tool '{uuid_or_name}': {e}")
            raise

    def delete(self, uuid_or_name: str) -> Dict[str, Any]:
        """Delete a tool and its associated files.

        Removes the tool metadata, module files, cache entries, and description indexes.

        Args:
            uuid_or_name: Tool UUID or name to delete.

        Returns:
            Dict[str, Any]: ``{"uuid": <deleted-tool-uuid>}``.

        Raises:
            KeyError: If tool not found.
        """
        delete_tool_counter.inc()
        try:
            uuid = self._resolve_uuid(uuid_or_name)
            with self.handler.write_lock(uuid):
                dependents = self.handler.dependency_manager.get_dependents(uuid)
                if dependents:
                    raise ObjectInUseError("tool", uuid, dependents)
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
                self.remove_dependent("tool", uuid)
                if self.handler.descriptions:
                    try:
                        self.handler.descriptions.delete_description(uuid)
                    except Exception as e:
                        logger.warning(
                            f"Could not delete tool description for {uuid}: {e}"
                        )
                emit_content_deleted("tool", uuid)
                logger.info(f"Tool '{uuid_or_name}' deleted")
                return {"uuid": uuid}
        except (KeyError, ObjectInUseError):
            raise
        except Exception as e:
            logger.error(f"Error deleting tool '{uuid_or_name}': {e}")
            raise

    def add_from_python(
        self,
        file_bytes: bytes,
        file_name: Optional[str] = None,
        selected_func: Optional[str] = None,
        update_existing: bool = False,
    ) -> Dict[str, Any]:
        """Create or update a tool from a Python source file.

        Parses the file's docstring to extract function name, description,
        parameters, and return type, then either creates a new tool or updates
        an existing one with the same name.

        For the create path, dependency auto-detection runs inside
        :meth:`create`. For the update path, dependency auto-detection happens
        here because :meth:`update` does not handle the module file or
        re-detect dependencies.

        Args:
            file_bytes: Python file contents.
            file_name: Original filename (used as ``module_name``). Falls back
                to ``"<func_name>.py"`` when ``None``.
            selected_func: Optional name of the specific function to extract.
                If ``None``, the first function in the file is used.
            update_existing: If True and a tool with the same name exists,
                update it (re-writing its module file and refreshing its
                manifest). Otherwise a new tool is created.

        Returns:
            Dict[str, Any]: ``{"message", "name", "uuid", "module_name",
                "parameters", "description", "action"}`` where ``action`` is
                ``"created"`` or ``"updated"``.

        Raises:
            ValueError: If the file cannot be parsed or its docstring is
                missing a short description.
        """
        from skillberry_store.utils.python_utils import extract_docstring

        add_tool_from_python_counter.inc()
        try:
            func_name, docstring_obj = extract_docstring(file_bytes, selected_func)
        except Exception as e:
            raise ValueError(
                f"Failed to parse Python code or extract docstring: {e}. "
                "Ensure the function has a properly formatted docstring with parameters."
            )
        description = docstring_obj.short_description
        if not description:
            raise ValueError("Function docstring must include a description.")

        params_properties: Dict[str, Any] = {}
        required_params: List[str] = []
        for param in docstring_obj.params:
            params_properties[param.arg_name] = {
                "type": param.type_name if param.type_name else "string",
                "description": param.description if param.description else "",
            }
            required_params.append(param.arg_name)

        returns_dict: Optional[Dict[str, Any]] = None
        if docstring_obj.returns:
            returns_dict = {
                "type": docstring_obj.returns.type_name or None,
                "description": docstring_obj.returns.description or None,
            }

        module_filename = file_name if file_name else f"{func_name}.py"
        existing_tool = self.handler.lookup_by_name(func_name)

        if update_existing and existing_tool:
            tool_uuid = generate_or_validate_uuid(existing_tool.get("uuid"))
            self.handler.write_file(tool_uuid, module_filename, file_bytes)
            data: Dict[str, Any] = {
                "name": func_name,
                "uuid": tool_uuid,
                "description": description,
                "programming_language": "python",
                "packaging_format": "code",
                "module_name": module_filename,
                "version": "0.0.1",
                "state": "approved",
                "params": {
                    "type": "object",
                    "properties": params_properties,
                    "required": required_params,
                    "optional": [],
                },
            }
            if returns_dict:
                data["returns"] = returns_dict
            if is_auto_detect_dependencies_enabled():
                try:
                    content_str = (
                        file_bytes.decode("utf-8")
                        if isinstance(file_bytes, bytes)
                        else file_bytes
                    )
                    available = self.handler.get_existing_names()
                    detected = detect_tool_dependencies(
                        content_str, func_name, available
                    )
                    if detected:
                        data["dependencies"] = [
                            self.handler.name_to_uuid(n) for n in detected
                        ]
                except Exception as e:
                    logger.warning(f"Failed to auto-detect dependencies: {e}")
            self.update(tool_uuid, data)
            return {
                "message": f"Tool '{func_name}' updated successfully.",
                "name": func_name,
                "uuid": tool_uuid,
                "module_name": module_filename,
                "parameters": params_properties,
                "description": description,
                "action": "updated",
            }

        data = {
            "name": func_name,
            "description": description,
            "programming_language": "python",
            "packaging_format": "code",
            "version": "0.0.1",
            "state": "approved",
            "params": {
                "type": "object",
                "properties": params_properties,
                "required": required_params,
                "optional": [],
            },
        }
        if returns_dict:
            data["returns"] = returns_dict
        result = self.create(
            data,
            module_content=file_bytes,
            module_filename=module_filename,
        )
        return {
            "message": f"Tool '{result['name']}' created successfully.",
            "name": result["name"],
            "uuid": result["uuid"],
            "module_name": result["module_name"],
            "parameters": params_properties,
            "description": description,
            "action": "created",
        }

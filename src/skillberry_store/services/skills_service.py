"""Business logic for skill CRUD operations."""

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
prom_prefix = "sts_service_skills_"
create_skill_counter = Counter(
    f"{prom_prefix}create_skill_counter", "Count number of skill create operations"
)
list_skills_counter = Counter(
    f"{prom_prefix}list_skills_counter", "Count number of skill list operations"
)
get_skill_counter = Counter(
    f"{prom_prefix}get_skill_counter", "Count number of skill get operations"
)
delete_skill_counter = Counter(
    f"{prom_prefix}delete_skill_counter", "Count number of skill delete operations"
)
update_skill_counter = Counter(
    f"{prom_prefix}update_skill_counter", "Count number of skill update operations"
)
search_skills_counter = Counter(
    f"{prom_prefix}search_skills_counter", "Count number of skill search operations"
)
detect_anthropic_skills_counter = Counter(
    f"{prom_prefix}detect_anthropic_skills_counter",
    "Count number of detect-anthropic-skills operations",
)
import_anthropic_skill_counter = Counter(
    f"{prom_prefix}import_anthropic_skill_counter",
    "Count number of import-anthropic-skill operations",
)
export_anthropic_skill_counter = Counter(
    f"{prom_prefix}export_anthropic_skill_counter",
    "Count number of export-anthropic-skill operations",
)


class GithubApiError(Exception):
    """Error returned from a GitHub API call.

    Carries the upstream HTTP ``status_code`` so callers can surface a faithful
    error to their own clients without becoming FastAPI-aware.
    """

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class SkillsService:
    """Service layer for skill CRUD operations.

    Provides business logic for managing skills, which are high-level compositions
    that group related tools and snippets together. Sibling-service operations
    (e.g. resolving tool/snippet objects in :meth:`populate_objects`,
    :meth:`import_anthropic`, :meth:`export_anthropic`, and :meth:`delete`'s
    cascade path) are routed through
    :func:`skillberry_store.services.registry.get_service`.

    Attributes:
        handler: ObjectHandler for skill persistence operations.
        descriptions: accessed via ``handler.descriptions`` (not stored as a separate attribute).
    """

    def __init__(
        self,
        handler: ObjectHandler,
    ):
        """Initialize the SkillsService.

        Args:
            handler: ObjectHandler instance for skill operations.
        """
        self.handler = handler


    def add_dependent(
        self, referencing_type: str, referencing_uuid: str, referenced_skill_uuids: List[str]
    ) -> None:
        """Register that ``referencing_uuid`` depends on each UUID in ``referenced_skill_uuids``.

        Called by ``VmcpService`` and ``VnfsService`` when they create or update a server
        that references a skill.

        Args:
            referencing_type: Object type of the referencing object (e.g. ``"vmcp"``).
            referencing_uuid: UUID of the referencing object.
            referenced_skill_uuids: UUIDs of the skills being depended on.
        """
        self.handler.dependency_manager.add(
            referencing_type, referencing_uuid, referenced_skill_uuids
        )

    def remove_dependent(self, referencing_type: str, referencing_uuid: str) -> None:
        """Remove all dependency records where ``referencing_uuid`` is the referencing side.

        Called when the referencing object is updated or deleted.

        Args:
            referencing_type: Object type of the referencing object.
            referencing_uuid: UUID of the referencing object.
        """
        self.handler.dependency_manager.remove_referencing(referencing_type, referencing_uuid)

    def _resolve_uuid(self, uuid_or_name: str) -> str:
        """Resolve a skill identifier to its UUID.
        
        Args:
            uuid_or_name: Skill UUID or name to resolve.
            
        Returns:
            str: The resolved UUID.
            
        Raises:
            KeyError: If skill not found.
        """
        try:
            return self.handler.resolve_to_uuid_or_error(uuid_or_name)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"Skill '{uuid_or_name}' not found")
            raise

    def populate_objects(self, skill_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Populate full tool and snippet objects from their UUIDs.

        Resolves ``tool_uuids`` and ``snippet_uuids`` to their complete metadata
        objects via the sibling :class:`ToolsService` / :class:`SnippetsService`
        singletons (obtained from
        :func:`skillberry_store.services.registry.get_service`) and adds them
        as ``tools`` and ``snippets`` lists in the skill dictionary.

        Args:
            skill_dict: Skill dictionary containing tool_uuids and snippet_uuids.

        Returns:
            Dict[str, Any]: The skill dictionary with 'tools' and 'snippets' populated.

        Raises:
            RuntimeError: If any referenced tool or snippet is missing or invalid.
        """
        from skillberry_store.services.registry import get_service

        if skill_dict.get("tool_uuids"):
            try:
                tools_service = get_service("tool")
                skill_dict["tools"] = [
                    tools_service.get(uuid) for uuid in skill_dict["tool_uuids"]
                ]
            except Exception as e:
                raise RuntimeError(
                    f"Skill '{skill_dict.get('name')}' references missing tools: {e}"
                )
        else:
            skill_dict["tools"] = []
        if skill_dict.get("snippet_uuids"):
            try:
                snippets_service = get_service("snippet")
                skill_dict["snippets"] = [
                    snippets_service.get(uuid) for uuid in skill_dict["snippet_uuids"]
                ]
            except Exception as e:
                raise RuntimeError(
                    f"Skill '{skill_dict.get('name')}' references missing snippets: {e}"
                )
        else:
            skill_dict["snippets"] = []
        return skill_dict

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new skill.
        
        Creates a skill entry with metadata and updates caches and indexes.
        Skills reference tools and snippets by their UUIDs.
        
        Args:
            data: Skill metadata dictionary (name, description, tool_uuids, snippet_uuids, etc.).
            
        Returns:
            Dict[str, Any]: The created skill data with UUID and timestamps.
            
        Raises:
            ValueError: If skill with the same UUID already exists.
        """
        create_skill_counter.inc()
        try:
            data["uuid"] = generate_or_validate_uuid(data.get("uuid"))
            if self.handler.object_exists(data["uuid"]):
                raise ValueError(f"Skill with UUID '{data['uuid']}' already exists")
            now = datetime.now(timezone.utc).isoformat()
            data.setdefault("created_at", now)
            data["modified_at"] = now
            if data.get("name"):
                data["parent"] = self.handler.get_cache_parent_for_head(
                    data["uuid"], data["name"]
                )
            self.handler.write_dict(data["uuid"], data)
            from skillberry_store.services.registry import get_service
            get_service("tool").add_dependent(
                "skill", data["uuid"], data.get("tool_uuids") or []
            )
            get_service("snippet").add_dependent(
                "skill", data["uuid"], data.get("snippet_uuids") or []
            )
            if data.get("name"):
                self.handler.update_cache(data["uuid"], new_name=data["name"])
            if self.handler.descriptions and data.get("description"):
                self.handler.descriptions.write_description(data["uuid"], data["description"])
            emit_content_added("skill", data["uuid"])
            logger.info(f"Skill '{data.get('name')}' created with UUID {data['uuid']}")
            return data
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error creating skill '{data.get('name')}': {e}")
            raise

    def _safe_read(self, uuid: str, label: str) -> Dict[str, Any]:
        """Safely read a skill dictionary with error handling.
        
        Args:
            uuid: Skill UUID to read.
            label: Human-readable label for error messages.
            
        Returns:
            Dict[str, Any]: Skill metadata dictionary.
            
        Raises:
            KeyError: If skill not found.
        """
        try:
            return self.handler.read_dict(uuid)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"Skill '{label}' not found")
            raise

    def get(self, uuid_or_name: str) -> Dict[str, Any]:
        """Get skill metadata by UUID or name with populated tool and snippet objects.

        Args:
            uuid_or_name: Skill UUID or name.

        Returns:
            Dict[str, Any]: Skill metadata dictionary with 'tools' and 'snippets' populated.

        Raises:
            KeyError: If skill not found.
        """
        get_skill_counter.inc()
        try:
            uuid = self._resolve_uuid(uuid_or_name)
            with self.handler.read_lock(uuid):
                skill = self._safe_read(uuid, uuid_or_name)
                try:
                    return self.populate_objects(skill)
                except RuntimeError as e:
                    logger.warning(str(e))
                    skill.setdefault("tools", [])
                    skill.setdefault("snippets", [])
                    return skill
        except KeyError:
            raise
        except Exception as e:
            logger.error(f"Error retrieving skill '{uuid_or_name}': {e}")
            raise

    def list_all(self, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """List all skills with optional filtering and populated objects.

        Args:
            filters: Optional dictionary of field:value pairs to filter by.

        Returns:
            List[Dict[str, Any]]: List of skill metadata dictionaries with tools and snippets populated,
                                  sorted by modified_at descending.
        """
        list_skills_counter.inc()
        try:
            items = self.handler.list_all_dicts()
            if filters:
                items = [
                    i for i in items if all(i.get(k) == v for k, v in filters.items())
                ]
            for item in items:
                try:
                    self.populate_objects(item)
                except RuntimeError as e:
                    logger.warning(str(e))
                    item.setdefault("tools", [])
                    item.setdefault("snippets", [])
            items.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
            return items
        except Exception as e:
            logger.error(f"Error listing skills: {e}")
            raise

    def search(
        self,
        search_term: str,
        max_number_of_results: int = 5,
        similarity_threshold: float = 1.0,
        manifest_filter: str = ".",
        lifecycle_state: Optional["LifecycleState"] = None,
    ) -> List[Dict[str, Any]]:
        """Search skills by semantic similarity to a search term.

        Performs a vector-similarity search over skill descriptions, then filters
        by similarity threshold, manifest properties, and lifecycle state, and
        returns matched names with similarity scores sorted by ``modified_at``
        (most recent first).

        Args:
            search_term: Free-text query to match against skill descriptions.
            max_number_of_results: Upper bound on candidates returned by the
                vector index before threshold filtering.
            similarity_threshold: Maximum allowed similarity score (lower is
                more similar). Candidates above this score are discarded.
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

        search_skills_counter.inc()
        try:
            if lifecycle_state is None:
                lifecycle_state = LifecycleState.ANY
            if not self.handler.descriptions:
                raise RuntimeError(
                    "Skill search is not available - descriptions not initialized"
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
                skill_uuid = matched.get("filename")
                if not skill_uuid:
                    continue
                try:
                    skill_dict = self.handler.read_dict(skill_uuid)
                    skill_dict["similarity_score"] = matched.get(
                        "similarity_score", 0.0
                    )
                    candidates.append(skill_dict)
                except Exception as e:
                    logger.warning(f"Could not load skill {skill_uuid}: {e}")
            filtered_skills = apply_search_filters(
                candidates,
                manifest_filter=manifest_filter,
                lifecycle_state=lifecycle_state,
            )
            filtered_skills.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
            return [
                {
                    "filename": s.get("name", ""),
                    "similarity_score": s.get("similarity_score", 0.0),
                }
                for s in filtered_skills
                if s.get("name")
            ]
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Error searching skills: {e}")
            raise

    def update(self, uuid_or_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing skill's metadata.

        Merges new data with existing skill data, updates timestamps, caches,
        and description indexes as needed.

        Args:
            uuid_or_name: Skill UUID or name to update.
            data: Dictionary of fields to update.

        Returns:
            Dict[str, Any]: The updated skill metadata.

        Raises:
            KeyError: If skill not found.
        """
        update_skill_counter.inc()
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
                from skillberry_store.services.registry import get_service
                get_service("tool").remove_dependent("skill", uuid)
                get_service("snippet").remove_dependent("skill", uuid)
                self.handler.write_dict(uuid, merged)
                get_service("tool").add_dependent(
                    "skill", uuid, merged.get("tool_uuids") or []
                )
                get_service("snippet").add_dependent(
                    "skill", uuid, merged.get("snippet_uuids") or []
                )
                if new_name:
                    self.handler.update_cache(
                        uuid, new_name=new_name, old_name=old_name, old_parent=old_parent
                    )
                if self.handler.descriptions and merged.get("description"):
                    self.handler.descriptions.write_description(uuid, merged["description"])
                emit_content_updated("skill", uuid)
                logger.info(f"Skill '{uuid_or_name}' updated")
                return merged
        except KeyError:
            raise
        except Exception as e:
            logger.error(f"Error updating skill '{uuid_or_name}': {e}")
            raise

    def detect_anthropic_skills(
        self,
        source_type: str,
        github_url: Optional[str] = None,
        folder_path: Optional[str] = None,
        override_token: Optional[str] = None,
        anonymous: bool = True,
    ) -> List[str]:
        """Detect child skill directories in a parent location.

        Scans a parent location (GitHub URL or local folder) and returns the
        names of subdirectories that contain a ``SKILL.md`` file.

        Args:
            source_type: ``"url"`` or ``"folder"``.
            github_url: GitHub repository URL. Required when
                ``source_type == "url"``.
            folder_path: Local folder path. Required when
                ``source_type == "folder"``. Must resolve to a path within the
                current user's home directory.
            override_token: Optional auth token forwarded to the
                per-endpoint auth resolver.
            anonymous: Whether to attempt anonymous GitHub access.

        Returns:
            List[str]: Names of subdirectories that contain ``SKILL.md``.

        Raises:
            ValueError: If inputs are invalid (missing required field, bad
                ``source_type``, folder outside home, folder does not exist or
                is not a directory).
            ReauthRequired: If interactive re-authentication is needed for the
                GitHub endpoint. Propagated untouched from the auth resolver.
            GithubApiError: If GitHub returns a non-OK response while listing
                the parent or child directories.
            RuntimeError: For unexpected filesystem errors while reading the
                local folder.
        """
        import os
        import re

        import requests

        from skillberry_store.tools.endpoint_auth import (
            ReauthRequired,
            resolve_auth_headers,
        )

        detect_anthropic_skills_counter.inc()
        logger.info(f"Request to detect Anthropic skills from {source_type}")
        try:
            skill_paths: List[str] = []

            if source_type == "url":
                if not github_url:
                    raise ValueError("github_url is required for source_type='url'")
                auth_headers = resolve_auth_headers(
                    github_url,
                    override_token=override_token,
                    anonymous=anonymous,
                )
                api_url = github_url.replace("github.com", "api.github.com/repos")
                api_url = re.sub(r"/tree/(main|master)/", r"/contents/", api_url)
                logger.info(f"Fetching directory listing from: {api_url}")
                response = requests.get(api_url, headers=auth_headers, timeout=30)
                if not response.ok:
                    raise GithubApiError(
                        response.status_code,
                        f"GitHub API error: {response.text or response.reason}",
                    )
                items = response.json()
                for item in items:
                    if item["type"] == "dir":
                        dir_name = item["name"]
                        dir_api_url = item["url"]
                        try:
                            dir_response = requests.get(
                                dir_api_url, headers=auth_headers, timeout=30
                            )
                            if dir_response.ok:
                                dir_items = dir_response.json()
                                has_skill_md = any(
                                    f["name"].upper() == "SKILL.MD"
                                    and f["type"] == "file"
                                    for f in dir_items
                                )
                                if has_skill_md:
                                    skill_paths.append(dir_name)
                                    logger.info(
                                        f"Found skill directory: {dir_name}"
                                    )
                        except Exception as e:
                            logger.warning(
                                f"Failed to check directory {dir_name}: {e}"
                            )
            elif source_type == "folder":
                if not folder_path:
                    raise ValueError(
                        "folder_path is required for source_type='folder'"
                    )
                home_dir = os.path.realpath(os.path.expanduser("~"))
                abs_input = os.path.realpath(folder_path)
                if not (
                    abs_input == home_dir
                    or abs_input.startswith(home_dir + os.sep)
                ):
                    raise ValueError(
                        "folder_path must be within the current user's home directory"
                    )
                if abs_input == home_dir:
                    safe_root = home_dir
                else:
                    rel = abs_input[len(home_dir) + len(os.sep) :]
                    clean_parts = [
                        os.path.basename(p) for p in rel.split(os.sep) if p
                    ]
                    safe_root = os.path.join(home_dir, *clean_parts)
                if not os.path.exists(safe_root):
                    raise ValueError("Folder does not exist")
                if not os.path.isdir(safe_root):
                    raise ValueError("Path is not a directory")
                try:
                    for entry in os.listdir(safe_root):  # lgtm[py/path-injection]
                        if entry != os.path.basename(entry):
                            continue
                        entry_path = os.path.join(safe_root, entry)
                        if os.path.realpath(entry_path).startswith(
                            safe_root + os.sep
                        ) and os.path.isdir(entry_path):
                            skill_md_path = os.path.join(entry_path, "SKILL.md")
                            if os.path.isfile(skill_md_path):
                                skill_paths.append(entry)
                                logger.info(f"Found skill directory: {entry}")
                except Exception as e:
                    raise RuntimeError(f"Error reading directory: {str(e)}")
            else:
                raise ValueError(
                    f"Invalid source_type: {source_type}. Must be 'url' or 'folder'"
                )
            logger.info(f"Detected {len(skill_paths)} skill directories")
            return skill_paths
        except (ValueError, ReauthRequired, GithubApiError, RuntimeError):
            raise
        except Exception as e:
            logger.error(f"Error detecting Anthropic skills: {e}")
            raise

    def export_anthropic(
        self, uuid_or_name: str, allow_invalid_name: bool = False
    ) -> bytes:
        """Export a skill to the Anthropic format as a ZIP byte payload.

        Resolves the skill, gathers its tools (with their module contents) and
        snippets via the sibling :class:`ToolsService` / :class:`SnippetsService`
        singletons (obtained from
        :func:`skillberry_store.services.registry.get_service`), and produces a
        ZIP archive in the Anthropic skill layout.

        Args:
            uuid_or_name: Skill UUID or name to export.
            allow_invalid_name: When True, skip the default slug validation on
                the skill's ``name``. Anthropic conventions expect the folder
                name (== ``name`` in ``SKILL.md`` frontmatter) to be a slug.

        Returns:
            bytes: The ZIP archive contents. Caller is responsible for setting
                content disposition / media type.

        Raises:
            KeyError: If the skill is not found.
            InvalidSkillNameError: If the name is not slug-safe and
                ``allow_invalid_name`` is False.
        """
        from skillberry_store.services.registry import get_service
        from skillberry_store.tools.anthropic.exporter import (
            export_skill_to_anthropic_format,
        )

        export_anthropic_skill_counter.inc()
        logger.info(f"Request to export skill to Anthropic format: {uuid_or_name}")
        try:
            skill_uuid = self._resolve_uuid(uuid_or_name)
            with self.handler.read_lock(skill_uuid):
                skill_dict = self._safe_read(skill_uuid, uuid_or_name)
                tools_service = get_service("tool")
                snippets_service = get_service("snippet")

                tools: List[Dict[str, Any]] = []
                tool_modules: Dict[str, str] = {}
                for tool_uuid in skill_dict.get("tool_uuids") or []:
                    tool_dict = tools_service.get(tool_uuid)
                    tools.append(tool_dict)
                    tool_name = tool_dict.get("name")
                    module_name = tool_dict.get("module_name")
                    if tool_name and module_name:
                        try:
                            tool_modules[tool_name] = tools_service.get_module(tool_uuid)
                        except Exception as e:
                            logger.warning(
                                f"Could not read module for tool {tool_name}: {e}"
                            )

                snippets: List[Dict[str, Any]] = [
                    snippets_service.get(snippet_uuid)
                    for snippet_uuid in skill_dict.get("snippet_uuids") or []
                ]

                zip_content = export_skill_to_anthropic_format(
                    skill=skill_dict,
                    tools=tools,
                    snippets=snippets,
                    tool_modules=tool_modules,
                    allow_invalid_name=allow_invalid_name,
                )
            logger.info(
                f"Successfully exported skill '{uuid_or_name}' to Anthropic format"
            )
            return zip_content
        except KeyError:
            raise
        except Exception as e:
            logger.error(
                f"Error exporting skill '{uuid_or_name}' to Anthropic format: {e}"
            )
            raise

    def import_anthropic(
        self,
        source_type: str,
        source_data: Any,
        snippet_mode: str = "file",
        treat_all_as_documents: bool = False,
        tags: Optional[List[str]] = None,
        override_token: Optional[str] = None,
        anonymous: bool = True,
        github_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Import an Anthropic skill into the store.

        Imports tools, snippets, and the skill manifest from an Anthropic skill
        source (URL, ZIP bytes, or folder path), creating each item via its
        respective service. Cross-tool dependencies within the imported batch
        are resolved by passing the batch's name->UUID map to
        ``ToolsService.create`` via its ``extra_name_to_uuid`` parameter, so
        no dependency detection is duplicated here.

        Args:
            source_type: ``"url"``, ``"zip"``, or ``"folder"``.
            source_data: GitHub URL (str), ZIP bytes (bytes), or folder path (str).
            snippet_mode: ``"file"`` or ``"paragraph"`` for snippet import mode.
            treat_all_as_documents: If True, treat all files as document snippets.
            tags: Additional tags applied to the skill, every imported tool, and
                every imported snippet.
            override_token: Optional auth token forwarded to the per-endpoint
                auth resolver.
            anonymous: Whether to attempt anonymous access.
            github_url: Original GitHub URL (for origin tracking) when
                ``source_type == "url"``. When set, the resulting skill's
                ``extra.origin`` is populated with parsed GitHub coordinates.

        Returns:
            Dict[str, Any]: ``{"skill_name", "skill_uuid", "tools_created",
                "snippets_created", "ignored_files"}``.

        Raises:
            ValueError: If ``source_type`` is not one of ``"url"``, ``"zip"``,
                or ``"folder"``, or if ``source_data`` is missing for the
                given ``source_type``.
            ReauthRequired: If interactive re-authentication is required for
                the import source's endpoint.
        """
        from skillberry_store.services.registry import get_service
        from skillberry_store.tools.anthropic.importer import (
            import_from_anthropic_skill,
            parse_github_origin,
        )
        from skillberry_store.tools.endpoint_auth import ReauthRequired

        import_anthropic_skill_counter.inc()
        logger.info(f"Request to import Anthropic skill from {source_type}")
        try:
            if source_type not in ("url", "zip", "folder"):
                raise ValueError(
                    f"Invalid source_type: {source_type}. Must be 'url', 'zip', or 'folder'"
                )
            if not source_data:
                required_field = {
                    "url": "github_url",
                    "zip": "zip_file",
                    "folder": "folder_path",
                }[source_type]
                raise ValueError(
                    f"{required_field} is required for source_type='{source_type}'"
                )

            tags = tags or []
            tools_service = get_service("tool")
            snippets_service = get_service("snippet")

            (
                skill_name,
                skill_description,
                imported_tools,
                imported_snippets,
                ignored_files,
            ) = import_from_anthropic_skill(
                source_type=source_type,
                source_data=source_data,
                snippet_mode=snippet_mode,
                treat_all_as_documents=treat_all_as_documents,
                override_token=override_token,
                anonymous=anonymous,
            )

            # Pre-allocate tool UUIDs so cross-tool deps within this batch can be
            # resolved by ToolsService.create's auto-detection.
            all_tool_names: Dict[str, str] = {}
            for tool in imported_tools:
                tool.uuid = generate_or_validate_uuid(None)
                all_tool_names[tool.name] = tool.uuid

            created_tool_uuids: List[str] = []
            for tool in imported_tools:
                try:
                    tool_dict = tool.to_dict()
                    tool_name = tool_dict["name"]
                    ext = (
                        ".py"
                        if tool_dict["programmingLanguage"] == "python"
                        else ".sh"
                    )
                    module_filename = f"{tool_name}{ext}"
                    tool_tags = (
                        tool_dict["tags"].copy() if tool_dict["tags"] else []
                    )
                    for tag in tags:
                        if tag and tag not in tool_tags:
                            tool_tags.append(tag)
                    tool_data: Dict[str, Any] = {
                        "uuid": tool.uuid,
                        "name": tool_name,
                        "version": tool_dict["version"],
                        "description": tool_dict["description"],
                        "tags": tool_tags,
                        "programming_language": tool_dict["programmingLanguage"],
                        "packaging_format": "code",
                        "state": "approved",
                    }
                    if tool_dict.get("params"):
                        tool_data["params"] = tool_dict["params"]
                    if tool_dict.get("returns"):
                        tool_data["returns"] = tool_dict["returns"]
                    tools_service.create(
                        tool_data,
                        module_content=tool_dict["moduleContent"],
                        module_filename=module_filename,
                        extra_name_to_uuid=all_tool_names,
                    )
                    created_tool_uuids.append(tool.uuid)
                except Exception as e:
                    logger.error(f"Failed to create tool {tool.name}: {e}")

            created_snippet_uuids: List[str] = []
            for snippet in imported_snippets:
                try:
                    snippet_dict = snippet.to_dict()
                    snippet_tags = (
                        snippet_dict["tags"].copy() if snippet_dict["tags"] else []
                    )
                    for tag in tags:
                        if tag and tag not in snippet_tags:
                            snippet_tags.append(tag)
                    snippet_data = {
                        "name": snippet_dict["name"],
                        "version": snippet_dict["version"],
                        "description": snippet_dict["description"],
                        "content": snippet_dict["content"],
                        "tags": snippet_tags,
                        "content_type": "text/plain",
                        "state": "approved",
                    }
                    result = snippets_service.create(snippet_data)
                    created_snippet_uuids.append(result["uuid"])
                except Exception as e:
                    logger.error(f"Failed to create snippet {snippet.name}: {e}")

            skill_tags = ["anthropic", "imported"]
            for tag in tags:
                if tag and tag not in skill_tags:
                    skill_tags.append(tag)

            skill_extra: Dict[str, Any] = {}
            if source_type == "url" and github_url:
                origin = parse_github_origin(github_url)
                skill_extra["origin"] = {
                    "type": "github" if origin else "url",
                    "url": github_url,
                    **(origin or {}),
                }

            skill_data: Dict[str, Any] = {
                "name": skill_name,
                "version": "1.0.0",
                "description": skill_description,
                "tags": skill_tags,
                "tool_uuids": created_tool_uuids,
                "snippet_uuids": created_snippet_uuids,
                "state": "approved",
                "extra": skill_extra,
            }
            skill_result = self.create(skill_data)

            logger.info(
                f"Successfully imported Anthropic skill: "
                f"{skill_result.get('name', skill_name)}"
            )
            return {
                "skill_name": skill_result.get("name", skill_name),
                "skill_uuid": skill_result.get("uuid"),
                "tools_created": len(created_tool_uuids),
                "snippets_created": len(created_snippet_uuids),
                "ignored_files": ignored_files,
            }
        except (ValueError, ReauthRequired):
            raise
        except Exception as e:
            logger.error(f"Error importing Anthropic skill: {e}")
            raise

    def delete(
        self,
        uuid_or_name: str,
        delete_tools: bool = False,
        delete_snippets: bool = False,
    ) -> Dict[str, Any]:
        """Delete a skill, optionally cascading to its unshared tools and snippets.

        Removes the skill metadata, cache entries, and description indexes. When
        ``delete_tools`` (resp. ``delete_snippets``) is True, also deletes any tool
        (resp. snippet) referenced by this skill that is not referenced by any
        other skill. Sibling services are obtained from
        :func:`skillberry_store.services.registry.get_service`.

        Args:
            uuid_or_name: Skill UUID or name to delete.
            delete_tools: If True, cascade-delete tools that are not referenced
                by any other skill.
            delete_snippets: If True, cascade-delete snippets that are not
                referenced by any other skill.

        Returns:
            Dict[str, Any]: ``{"uuid": <deleted-skill-uuid>, "deleted_tools": [...],
                "deleted_snippets": [...]}``. The two lists are empty when no
                cascade is requested or no unshared item is found.

        Raises:
            KeyError: If skill not found.
        """
        from skillberry_store.services.registry import get_service

        delete_skill_counter.inc()
        try:
            uuid = self._resolve_uuid(uuid_or_name)
            with self.handler.write_lock(uuid):
                dependents = self.handler.dependency_manager.get_dependents(uuid)
                if dependents:
                    raise ObjectInUseError("skill", uuid, dependents)
                skill: Optional[Dict[str, Any]] = None
                try:
                    skill = self.handler.read_dict(uuid)
                except Exception:
                    pass
                deleted_tools: List[str] = []
                deleted_snippets: List[str] = []
                if skill is not None and (delete_tools or delete_snippets):
                    tools_service = get_service("tool")
                    snippets_service = get_service("snippet")
                    skill_uuid = skill.get("uuid") or uuid
                    all_skills = self.handler.list_all_dicts()
                    shared_tool_uuids: set = set()
                    shared_snippet_uuids: set = set()
                    for s in all_skills:
                        if s.get("uuid") != skill_uuid:
                            shared_tool_uuids.update(s.get("tool_uuids") or [])
                            shared_snippet_uuids.update(s.get("snippet_uuids") or [])
                    if delete_tools:
                        for tool_uuid in skill.get("tool_uuids") or []:
                            if tool_uuid not in shared_tool_uuids:
                                try:
                                    tools_service.delete(tool_uuid)
                                    deleted_tools.append(tool_uuid)
                                except Exception as e:
                                    logger.warning(
                                        f"Could not cascade-delete tool {tool_uuid}: {e}"
                                    )
                    if delete_snippets:
                        for snippet_uuid in skill.get("snippet_uuids") or []:
                            if snippet_uuid not in shared_snippet_uuids:
                                try:
                                    snippets_service.delete(snippet_uuid)
                                    deleted_snippets.append(snippet_uuid)
                                except Exception as e:
                                    logger.warning(
                                        f"Could not cascade-delete snippet {snippet_uuid}: {e}"
                                    )
                name = (skill or {}).get("name")
                parent = (skill or {}).get("parent")
                if uuid and name:
                    self.handler.update_cache(
                        uuid, new_name=None, old_name=name, old_parent=parent
                    )
                self.handler.delete_object(uuid)
                get_service("tool").remove_dependent("skill", uuid)
                get_service("snippet").remove_dependent("skill", uuid)
                if self.handler.descriptions:
                    try:
                        self.handler.descriptions.delete_description(uuid)
                    except Exception as e:
                        logger.warning(
                            f"Could not delete skill description for {uuid}: {e}"
                        )
                emit_content_deleted("skill", uuid)
                logger.info(f"Skill '{uuid_or_name}' deleted")
                return {
                    "uuid": uuid,
                    "deleted_tools": deleted_tools,
                    "deleted_snippets": deleted_snippets,
                }
        except (KeyError, ObjectInUseError):
            raise
        except Exception as e:
            logger.error(f"Error deleting skill '{uuid_or_name}': {e}")
            raise

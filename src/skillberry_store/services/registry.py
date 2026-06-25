"""Service registry: singleton access to *Service instances.

Mirrors the object-handler registry in ``skillberry_store.modules.object_handler``.
Initialize once at server startup with ``initialize_services(...)``; thereafter,
``get_service(<type>)`` returns the singleton for that object type.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from skillberry_store.modules.description import Description
    from skillberry_store.modules.vmcp_server_manager import VirtualMcpServerManager
    from skillberry_store.modules.vnfs_server_manager import VirtualNfsServerManager

logger = logging.getLogger(__name__)

_services: Dict[str, Any] = {}
_initialized = False


def initialize_services(
    *,
    tools_descriptions: Optional["Description"] = None,
    snippets_descriptions: Optional["Description"] = None,
    skills_descriptions: Optional["Description"] = None,
    vmcp_descriptions: Optional["Description"] = None,
    vnfs_descriptions: Optional["Description"] = None,
    vmcp_server_manager: Optional["VirtualMcpServerManager"] = None,
    vnfs_server_manager: Optional["VirtualNfsServerManager"] = None,
) -> None:
    """Initialize all service singletons. Idempotent.

    Each service is keyed by its object type ("tool", "snippet", "skill",
    "vmcp", "vnfs") and uses the singleton object handler from
    ``get_object_handler``.

    Args:
        tools_descriptions: Optional Description for tools.
        snippets_descriptions: Optional Description for snippets.
        skills_descriptions: Optional Description for skills.
        vmcp_descriptions: Optional Description for VMCP servers.
        vnfs_descriptions: Optional Description for vNFS servers.
        vmcp_server_manager: Required ``VirtualMcpServerManager`` for the
            VMCP service.
        vnfs_server_manager: Required ``VirtualNfsServerManager`` for the
            vNFS service.
    """
    global _initialized
    if _initialized:
        logger.warning("Services already initialized, skipping")
        return

    from skillberry_store.modules.object_handler import get_object_handler
    from skillberry_store.services.skills_service import SkillsService
    from skillberry_store.services.snippets_service import SnippetsService
    from skillberry_store.services.tools_service import ToolsService
    from skillberry_store.services.vmcp_service import VmcpService
    from skillberry_store.services.vnfs_service import VnfsService

    _services["tool"] = ToolsService(
        get_object_handler("tool"),
        tools_descriptions,
    )
    _services["snippet"] = SnippetsService(
        get_object_handler("snippet"),
        snippets_descriptions,
    )
    _services["skill"] = SkillsService(
        handler=get_object_handler("skill"),
        descriptions=skills_descriptions,
    )
    _services["vmcp"] = VmcpService(
        get_object_handler("vmcp"),
        vmcp_server_manager,
        vmcp_descriptions,
    )
    _services["vnfs"] = VnfsService(
        get_object_handler("vnfs"),
        vnfs_server_manager,
        vnfs_descriptions,
    )
    _initialized = True
    logger.info(
        f"Initialized {len(_services)} services: {list(_services.keys())}"
    )


def get_service(service_type: str) -> Any:
    """Return the singleton service for ``service_type``.

    Args:
        service_type: One of "tool", "snippet", "skill", "vmcp", "vnfs".

    Returns:
        The singleton service instance.

    Raises:
        RuntimeError: If services have not been initialized.
        ValueError: If the service type is not recognized.
    """
    if not _initialized:
        raise RuntimeError(
            "Services not initialized. Call initialize_services(...) first."
        )
    if service_type not in _services:
        raise ValueError(
            f"Unknown service type: '{service_type}'. "
            f"Valid types: {list(_services.keys())}"
        )
    return _services[service_type]


def clear_services() -> None:
    """Clear all services. Useful for testing.

    Resets the global state so the registry can be reinitialized. Should
    primarily be used in test cleanup.
    """
    global _initialized
    _services.clear()
    _initialized = False

"""Store components that plugins may instantiate privately.

Everything re-exported here is safe for a plugin to construct and own: it takes
its inputs through its constructor and does not require the core server's
process-global state (the service registry, the shared ``ObjectHandler``
singletons, or a running FastAPI app).

Plugins should import from here rather than from ``skillberry_store.modules.*``,
which is internal and offers no such guarantee.

- :class:`FileExecutor` — runs a single tool's code, given the source and a
  manifest. Depends on no store state at all. Use
  :meth:`FileExecutor.execute_file_sync` when you need to bound or abandon the
  execution from a thread you own; ``execute_file`` is the async equivalent.

- :class:`VirtualMcpServer` — serves a set of tools over MCP. Pass a
  ``tool_source`` to supply manifests and execution yourself, ``serve=False``
  for in-process dispatch with no port or transport, ``on_invoke=`` to observe
  every call including failures, and ``metrics_enabled=False`` to keep a
  short-lived instance out of the process metric series.

  **``tool_source`` is required while access control is enabled.** The core
  class falls back to the ``ObjectHandler`` singletons plus the service
  registry, which read manifests and module files, walk dependencies and
  execute — entirely outside ``StoreAPI`` and therefore outside admission
  control. That fallback is correct for the store's own managed servers; for a
  plugin it would be unguarded read and execute over every tool in the store,
  obtained with one import. Pass a source you got through ``StoreAPI`` (as
  ``dast``'s benign twin does) and the twin stays faithful *and* admitted.
  See plugin-identity §6.2.

Owning such an instance is code sharing, not an access-control bypass: a
privately constructed sandbox permits nothing ACL governs, and if a plugin
reimplemented container execution itself instead of importing it, nothing about
access control would change.
"""

from typing import Any, Optional

from skillberry_store.access_control.config import get_config as _get_acl_config
from skillberry_store.modules.file_executor import FileExecutor
from skillberry_store.modules.vmcp_server import (
    InvokeRecord,
    SnippetSource,
    ToolSource,
)
from skillberry_store.modules.vmcp_server import (
    VirtualMcpServer as _CoreVirtualMcpServer,
)

__all__ = [
    "FileExecutor",
    "InvokeRecord",
    "SnippetSource",
    "ToolSource",
    "VirtualMcpServer",
]


class VirtualMcpServer(_CoreVirtualMcpServer):
    """``VirtualMcpServer`` with the unguarded default source closed off.

    Identical to the core class in every respect except one: constructing it
    with no ``tool_source`` while access control is enabled raises, instead of
    silently falling back to the core singletons. The core class keeps its
    fallback — the store's own managed vMCP servers rely on it, and they are
    created through an endpoint the PDP already decided on.
    """

    def __init__(self, *args: Any, tool_source: Optional[Any] = None, **kwargs: Any):
        if tool_source is None and _get_acl_config().mode != "disabled":
            raise PermissionError(
                "VirtualMcpServer requires an explicit tool_source while access "
                "control is enabled: the default source reaches the ObjectHandler "
                "singletons and the service registry directly, bypassing "
                "admission control. Pass a source obtained through StoreAPI."
            )
        super().__init__(*args, tool_source=tool_source, **kwargs)

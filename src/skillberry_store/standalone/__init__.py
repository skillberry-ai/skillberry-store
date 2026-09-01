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

"""

from skillberry_store.modules.file_executor import FileExecutor

__all__ = [
    "FileExecutor",
]

"""Exceptions raised on a plugin's outward calls to the store.

Both are raised by ``StoreAPI._admit`` — enforcement point 2 — and both are
translated to HTTP by a pair of app-level handlers registered once in
``SBS.__init__``. Translation belongs on the app, not in plugin code: one
pair of handlers covers every plugin route without touching any plugin.

The split is between "the caller may not do this" and "this deployment is
misconfigured", because those want different status codes and different
audiences:

* :class:`PluginAuthorizationError` -> **403**. The identity is known and
  the PDP denied the operation. A caller should see it as their own
  authorization failure.
* :class:`PluginIdentityError` -> **500**. No identity is in scope at all
  (P5). Nobody did anything wrong; an owner tenant was never assigned.

**Neither handler fires on the event path**, where handlers run as
background tasks outside any request and ``_run_handler`` swallows every
exception into a log line. That is why ``_admit`` records the outcome on
the object itself rather than relying on the raise reaching a handler —
see :mod:`skillberry_store.plugins.outcomes`.
"""


class PluginStoreError(Exception):
    """Base class for a refused plugin store operation."""


class PluginAuthorizationError(PluginStoreError):
    """The plugin's identity is not granted this (resource, verb)."""


class PluginIdentityError(PluginStoreError):
    """No tenant identity is in scope for this operation (P5).

    An outward call attempted with no tenant assigned must fail rather than
    proceed anonymously. Assign an owner tenant — per plugin by enabling it
    as that tenant, or deployment-wide via ``plugins.owner_tenant`` in the
    access-control config.
    """

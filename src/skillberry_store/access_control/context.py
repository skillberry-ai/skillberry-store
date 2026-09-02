"""Ambient tenant identity, carried in a context variable.

See §4 of ``docs/design/plugin-identity.md``. A plugin has no request
object and no ``Subject`` parameter, so the identity its work runs under
is carried out-of-band:

* the **PEP** sets it from the authenticated caller, which is what makes
  a plugin's own API call run as the calling tenant (P3);
* the **event dispatcher** replaces it with the owning plugin's owner
  tenant, so trigger-driven work runs as the owner rather than as
  whoever happened to emit the event (P1, §4.3);
* ``StoreAPI._admit`` reads it — the only reader plugin authors ever
  reach indirectly. Plugin code never touches this module.

``contextvars`` is the async-native equivalent of thread-local storage,
and asyncio copies the context per task, so P3's "for the duration of one
API call" scoping comes for free with no unwind code. The one shape that
does **not** inherit a context is a thread the asyncio machinery did not
create — ``threading.Thread`` and ``loop.run_in_executor`` start empty
(``asyncio.to_thread`` and Starlette's threadpool both copy). Work
offloaded that way must carry the context explicitly::

    ctx = contextvars.copy_context()
    threading.Thread(target=ctx.run, args=(work,), daemon=True).start()

Never set from a value that leaked in from somewhere else: an empty
context must read as ``None`` so that an autonomous operation with no
assigned identity **fails** (P5) instead of silently inheriting an
earlier caller's tenant.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Optional

from skillberry_store.access_control.pdp import Subject

CURRENT_SUBJECT: ContextVar[Optional[Subject]] = ContextVar(
    "current_subject", default=None
)


def current_subject() -> Optional[Subject]:
    """The ambient subject, or ``None`` when no identity is in scope."""
    return CURRENT_SUBJECT.get()


def set_current_subject(subject: Optional[Subject]) -> Token:
    """Set the ambient subject; returns the token to ``reset`` it with."""
    return CURRENT_SUBJECT.set(subject)


def reset_current_subject(token: Token) -> None:
    """Restore whatever the ambient subject was before ``set_current_subject``."""
    CURRENT_SUBJECT.reset(token)

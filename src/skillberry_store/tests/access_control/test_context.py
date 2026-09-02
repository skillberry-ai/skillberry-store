"""The ambient subject context variable (plugin-identity §4.1, §4.2).

Propagation into every shape a plugin's work can run behind is what makes
identity reachable without threading a ``tenant_id`` through ~30
``StoreAPI`` methods. Two of the four ways to reach a thread do *not*
propagate, and one bundled plugin (dast) depends on knowing which.
"""

from __future__ import annotations

import asyncio
import contextvars
import threading
from concurrent.futures import ThreadPoolExecutor

from skillberry_store.access_control.context import (
    CURRENT_SUBJECT,
    current_subject,
    reset_current_subject,
    set_current_subject,
)
from skillberry_store.access_control.pdp import Subject


def test_default_is_none():
    assert current_subject() is None


def test_set_and_reset():
    token = set_current_subject(Subject(tenant_id="y"))
    try:
        assert current_subject().tenant_id == "y"
    finally:
        reset_current_subject(token)
    assert current_subject() is None


def test_propagates_into_create_task():
    """``emit_event`` dispatches handlers with ``loop.create_task``."""

    async def main():
        set_current_subject(Subject(tenant_id="y"))
        seen = {}

        async def child():
            seen["tenant"] = current_subject().tenant_id

        await asyncio.create_task(child())
        return seen["tenant"]

    assert asyncio.run(main()) == "y"


def test_task_set_does_not_leak_back_to_parent():
    """Each task owns a copied context, which is what makes ``_run_handler``'s
    owner override private to that handler (§4.3)."""

    async def main():
        set_current_subject(Subject(tenant_id="parent"))

        async def child():
            set_current_subject(Subject(tenant_id="child"))

        await asyncio.create_task(child())
        return current_subject().tenant_id

    assert asyncio.run(main()) == "parent"


def test_propagates_into_to_thread():
    """``dast`` offloads its whole scan with ``asyncio.to_thread``."""

    async def main():
        set_current_subject(Subject(tenant_id="y"))

        def work():
            return current_subject().tenant_id if current_subject() else None

        return await asyncio.to_thread(work)

    assert asyncio.run(main()) == "y"


def test_raw_thread_does_not_propagate_without_copy_context():
    """The rule the plugin contract states: a thread asyncio did not create
    for you starts with an empty context, so it must carry one explicitly."""
    set_current_subject(Subject(tenant_id="y"))
    box = {}

    def work():
        box["bare"] = current_subject()

    t = threading.Thread(target=work)
    t.start()
    t.join()
    assert box["bare"] is None

    ctx = contextvars.copy_context()
    t = threading.Thread(target=ctx.run, args=(work,))
    t.start()
    t.join()
    assert box["bare"].tenant_id == "y"
    CURRENT_SUBJECT.set(None)


def test_thread_pool_executor_does_not_propagate():
    set_current_subject(Subject(tenant_id="y"))
    with ThreadPoolExecutor(max_workers=1) as pool:
        assert pool.submit(current_subject).result() is None
    CURRENT_SUBJECT.set(None)

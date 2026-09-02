"""Owner tenant resolution and the event-path override.

Covers plugin-identity §5 (where the owner comes from, resolved lazily) and
§4.3 (trigger-driven work runs as the owner, never as the tenant whose
request happened to emit the event).

The §4.3 regression test is load-bearing rather than routine: because the
triggering tenant *is* ambiently present, the event path has to actively
override it. If that override is ever dropped the system silently reverts
to trigger inheritance and still looks correct — annotations still appear,
only the identity behind them is wrong.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional
from unittest.mock import Mock

import pytest

from skillberry_store.access_control.config import AccessControlConfig, User
from skillberry_store.access_control.context import (
    current_subject,
    set_current_subject,
)
from skillberry_store.access_control.pdp import Subject
from skillberry_store.plugins import events as plugin_events
from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType
from skillberry_store.plugins.config import PluginConfigStore
from skillberry_store.plugins.loader import PluginLoader
from skillberry_store.plugins.store_api import StoreAPI


@pytest.fixture(autouse=True)
def clean_event_registry():
    """Event state is module-global; restore it around every test."""
    saved_handlers = {k: list(v) for k, v in plugin_events._event_handlers.items()}
    saved_owners = dict(plugin_events._handler_owners)
    yield
    plugin_events._event_handlers.clear()
    plugin_events._event_handlers.update(saved_handlers)
    plugin_events._handler_owners.clear()
    plugin_events._handler_owners.update(saved_owners)
    plugin_events.set_enabled_resolver(None)
    plugin_events.set_owner_resolver(None)
    set_current_subject(None)


def _loader(tmp_path, cfg: Optional[AccessControlConfig] = None) -> PluginLoader:
    return PluginLoader(
        store_api=Mock(spec=StoreAPI),
        config_store=PluginConfigStore(path=tmp_path / "plugins.json"),
        acl_cfg=cfg,
    )


# ── §5.1: precedence ────────────────────────────────────────────────────── #


def test_no_owner_anywhere_resolves_to_none(tmp_path):
    loader = _loader(tmp_path, AccessControlConfig(mode="standalone"))
    assert loader.owner_tenant("sast") is None
    assert loader.owner_subject("sast") is None


def test_deployment_default_applies_when_no_record(tmp_path):
    cfg = AccessControlConfig(mode="standalone", plugin_owner_tenant="plugin-user")
    loader = _loader(tmp_path, cfg)
    assert loader.owner_tenant("sast") == "plugin-user"
    assert loader.owner_subject("sast").tenant_id == "plugin-user"


def test_per_plugin_record_beats_the_deployment_default(tmp_path):
    cfg = AccessControlConfig(mode="standalone", plugin_owner_tenant="plugin-user")
    loader = _loader(tmp_path, cfg)
    loader.record_owner("sast", "team-blue")
    assert loader.owner_tenant("sast") == "team-blue"
    # …and only for that plugin.
    assert loader.owner_tenant("provenance") == "plugin-user"


def test_record_owner_ignores_an_absent_tenant(tmp_path):
    """``disabled`` mode has no subject on the request, so there is nothing to
    record and nothing must be written (§2.5)."""
    loader = _loader(tmp_path, AccessControlConfig(mode="disabled"))
    loader.record_owner("sast", None)
    assert loader.config.owners() == {}


def test_owner_subject_carries_the_tenants_groups(tmp_path):
    cfg = AccessControlConfig(
        mode="standalone",
        users=[
            User(
                username="blue",
                tenant_id="team-blue",
                password_hash="x",
                groups=["scanners"],
            )
        ],
    )
    loader = _loader(tmp_path, cfg)
    loader.record_owner("sast", "team-blue")
    assert loader.owner_subject("sast").groups == ["scanners"]


def test_virtual_owner_subject_takes_groups_from_the_plugins_block(tmp_path):
    """``plugin-user`` has no ``standalone.users`` entry by design, so its
    groups can only come from the plugins block (§5.3)."""
    cfg = AccessControlConfig(
        mode="standalone",
        plugin_owner_tenant="plugin-user",
        plugin_owner_groups=["automation"],
    )
    loader = _loader(tmp_path, cfg)
    assert loader.owner_subject("sast").groups == ["automation"]


# ── §5.2: resolution is lazy ────────────────────────────────────────────── #


def test_owner_is_resolved_at_call_time_not_at_construction(tmp_path):
    """Plugins register handlers inside ``__init__``, before any tenant or
    config reload exists — so a later assignment has to take effect live."""
    cfg = AccessControlConfig(mode="standalone")
    loader = _loader(tmp_path, cfg)
    assert loader.owner_tenant("sast") is None
    cfg.plugin_owner_tenant = "plugin-user"
    assert loader.owner_tenant("sast") == "plugin-user"
    loader.record_owner("sast", "team-blue")
    assert loader.owner_tenant("sast") == "team-blue"


# ── §4.3: the event-path override ───────────────────────────────────────── #


class _Recorder(PluginBase):
    """A plugin that records the ambient tenant its handler observed."""

    slug = "recorder"

    def __init__(self):
        super().__init__()
        self.observed: list = []

        @plugin_events.on_content_added("skill")
        async def handle(uuid: str):
            s = current_subject()
            self.observed.append(s.tenant_id if s else None)

        self.handler = handle

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="Recorder",
            description="records the ambient tenant",
            version="1.0.0",
            plugin_type=PluginType.EVALUATOR,
        )

    def is_enabled(self) -> bool:
        return True

    def get_router(self):
        return None

    def get_cli_commands(self) -> Optional[Dict[str, Any]]:
        return None

    def get_ui_config(self) -> Optional[Dict[str, Any]]:
        return None


async def _emit_as(tenant: Optional[str]) -> None:
    """Emit content_added:skill from inside a request-like context."""
    if tenant is not None:
        set_current_subject(Subject(tenant_id=tenant))
    plugin_events.emit_content_added("skill", "uuid-1")
    # Let the dispatched tasks run to completion.
    await asyncio.gather(*list(plugin_events._background_tasks))


def test_handler_runs_as_the_owner_not_as_the_triggering_tenant(tmp_path):
    cfg = AccessControlConfig(mode="standalone", plugin_owner_tenant="plugin-user")
    loader = _loader(tmp_path, cfg)
    plugin = _Recorder()
    plugin_events.register_handler_owner(plugin.handler, "recorder")
    loader.plugins["recorder"] = plugin

    asyncio.run(_emit_as("uploader-tenant"))

    # Ambient inheritance would have given "uploader-tenant" here.
    assert plugin.observed == ["plugin-user"]


def test_sibling_handlers_observe_their_own_owners(tmp_path):
    cfg = AccessControlConfig(mode="standalone", plugin_owner_tenant="plugin-user")
    loader = _loader(tmp_path, cfg)
    a, b = _Recorder(), _Recorder()
    plugin_events.register_handler_owner(a.handler, "plugin-a")
    plugin_events.register_handler_owner(b.handler, "plugin-b")
    loader.record_owner("plugin-a", "team-blue")
    loader.record_owner("plugin-b", "team-green")

    asyncio.run(_emit_as("uploader-tenant"))

    assert a.observed == ["team-blue"]
    assert b.observed == ["team-green"]


def test_unassigned_owner_leaves_the_handler_with_no_identity(tmp_path):
    """Not an error at dispatch: the handler runs, and P5 fails at its first
    outward call with a message naming the missing assignment."""
    loader = _loader(tmp_path, AccessControlConfig(mode="standalone"))
    plugin = _Recorder()
    plugin_events.register_handler_owner(plugin.handler, "recorder")
    loader.plugins["recorder"] = plugin

    asyncio.run(_emit_as("uploader-tenant"))

    assert plugin.observed == [None]


def test_override_does_not_leak_back_to_the_emitting_context(tmp_path):
    cfg = AccessControlConfig(mode="standalone", plugin_owner_tenant="plugin-user")
    loader = _loader(tmp_path, cfg)
    plugin = _Recorder()
    plugin_events.register_handler_owner(plugin.handler, "recorder")
    loader.plugins["recorder"] = plugin

    async def main():
        set_current_subject(Subject(tenant_id="uploader-tenant"))
        plugin_events.emit_content_added("skill", "uuid-1")
        await asyncio.gather(*list(plugin_events._background_tasks))
        return current_subject().tenant_id

    assert asyncio.run(main()) == "uploader-tenant"
    assert plugin.observed == ["plugin-user"]


def test_a_broken_owner_resolver_grants_no_identity(tmp_path):
    plugin = _Recorder()
    plugin_events.register_handler_owner(plugin.handler, "recorder")

    def boom(slug):
        raise RuntimeError("config unreadable")

    plugin_events.set_owner_resolver(boom)
    asyncio.run(_emit_as("uploader-tenant"))
    assert plugin.observed == [None]


def test_handler_with_no_recorded_owner_gets_no_identity(tmp_path):
    """A handler the loader never attributed (registered outside discovery)."""
    cfg = AccessControlConfig(mode="standalone", plugin_owner_tenant="plugin-user")
    _loader(tmp_path, cfg)
    plugin = _Recorder()  # deliberately not registered with an owner slug
    asyncio.run(_emit_as("uploader-tenant"))
    assert plugin.observed == [None]

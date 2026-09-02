"""Enforcement point 2 — admission control inside ``StoreAPI``.

Covers plugin-identity §2.4 (``_admit``, the per-slug view, the closed
handler properties), §9.1 (``record_outcome``, and the circularity that
forces the framework rather than the plugin to write it) and P5 (an
outward call with no tenant fails rather than proceeding anonymously).
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from skillberry_store.access_control.config import (
    AccessControlConfig,
    Role,
    RoleBinding,
    Rule,
    Subject as SubjectRef,
)
from skillberry_store.access_control.context import set_current_subject
from skillberry_store.access_control.pdp import Subject
from skillberry_store.plugins.errors import (
    PluginAuthorizationError,
    PluginIdentityError,
)
from skillberry_store.plugins.outcomes import (
    OUTCOME_ERROR,
    OUTCOME_SKIP,
    RECORDABLE_OUTCOMES,
    outcome_tag,
    record_outcome,
)
from skillberry_store.plugins.store_api import StoreAPI

DISABLED = AccessControlConfig(mode="disabled")


def _standalone(*, verbs, resources=("skills", "tools", "snippets")) -> AccessControlConfig:
    """A standalone config granting ``verbs`` on ``resources`` to 'owner'."""
    return AccessControlConfig(
        mode="standalone",
        roles=[
            Role(
                name="plugin-agent",
                rules=[Rule(resources=list(resources), verbs=list(verbs))],
            )
        ],
        bindings=[
            RoleBinding(
                name="b",
                subjects=[SubjectRef(kind="tenant", name="owner")],
                roles=["plugin-agent"],
            )
        ],
    )


def _services(store: dict | None = None) -> dict:
    """Mock services whose handlers read/write an in-memory object store."""
    store = store if store is not None else {}

    def make(kind):
        svc = MagicMock()
        svc.get.return_value = {"uuid": "u1", "tags": []}
        svc.list_all.return_value = []
        handler = MagicMock()

        def read_dict(uuid):
            if uuid not in store:
                raise KeyError(uuid)
            return store[uuid]

        def write_dict(uuid, obj):
            store[uuid] = obj

        handler.read_dict.side_effect = read_dict
        handler.write_dict.side_effect = write_dict
        svc.handler = handler
        return svc

    vmcp = MagicMock()
    vmcp.create.return_value = {"uuid": "v1"}
    vmcp.get.return_value = {"uuid": "v1"}
    vmcp.list_all.return_value = []
    return {
        "skills": make("skills"),
        "tools": make("tools"),
        "snippets": make("snippets"),
        "vmcp": vmcp,
        "_store": store,
    }


@pytest.fixture(autouse=True)
def clear_ambient_subject():
    yield
    set_current_subject(None)


def _api(cfg, services=None, slug="sast") -> StoreAPI:
    services = services if services is not None else _services()
    return StoreAPI(services, cfg).for_plugin(slug)


# ── disabled mode: every mechanism inert ────────────────────────────────── #


def test_disabled_mode_admits_without_a_subject():
    """No tenants exist, so there is nothing to decide — and P5 must not fire."""
    api = _api(DISABLED)
    assert api.acl_enabled is False
    api.get_skill("u1")  # would raise PluginIdentityError under ACL
    api.update_skill_tags("u1", ["x"])


def test_disabled_mode_keeps_the_handler_properties_usable():
    """Their setters are how tests inject fakes."""
    api = _api(DISABLED)
    fake = object()
    api.skills = fake
    with pytest.warns(DeprecationWarning):
        assert api.skills is fake


# ── the per-slug view ───────────────────────────────────────────────────── #


def test_for_plugin_shares_services_but_carries_its_own_slug():
    services = _services()
    shared = StoreAPI(services, DISABLED)
    a, b = shared.for_plugin("sast"), shared.for_plugin("dast")
    assert shared.slug is None
    assert (a.slug, b.slug) == ("sast", "dast")
    assert a.skills_service is b.skills_service is services["skills"]


# ── P5: no identity means failure, not anonymity ────────────────────────── #


def test_no_ambient_subject_raises_identity_error():
    api = _api(_standalone(verbs=["update"]))
    with pytest.raises(PluginIdentityError) as exc:
        api.update_skill_tags("u1", ["x"])
    assert "owner tenant" in str(exc.value)


def test_subject_with_no_tenant_raises_identity_error():
    api = _api(_standalone(verbs=["update"]))
    set_current_subject(Subject(tenant_id=None))
    with pytest.raises(PluginIdentityError):
        api.update_skill_tags("u1", ["x"])


# ── the PDP decides, on the same config ─────────────────────────────────── #


def test_granted_verb_is_admitted():
    api = _api(_standalone(verbs=["get", "update"]))
    set_current_subject(Subject(tenant_id="owner"))
    api.get_skill("u1")
    api.update_skill_tags("u1", ["x"])


def test_ungranted_verb_is_denied():
    api = _api(_standalone(verbs=["get"]))
    set_current_subject(Subject(tenant_id="owner"))
    api.get_skill("u1")
    with pytest.raises(PluginAuthorizationError):
        api.update_skill_tags("u1", ["x"])


def test_unbound_tenant_is_denied():
    api = _api(_standalone(verbs=["update"]))
    set_current_subject(Subject(tenant_id="somebody-else"))
    with pytest.raises(PluginAuthorizationError):
        api.update_skill_tags("u1", ["x"])


def test_execute_tool_needs_the_execute_verb():
    """The only execution path StoreAPI exposes — dast's twin runs the skill's
    own tools through it (§2.4, §8)."""
    api = _api(_standalone(verbs=["get", "update"], resources=["tools"]))
    set_current_subject(Subject(tenant_id="owner"))
    with pytest.raises(PluginAuthorizationError):
        asyncio.run(api.execute_tool("t1"))

    api = _api(_standalone(verbs=["execute"], resources=["tools"]))
    set_current_subject(Subject(tenant_id="owner"))
    api.tools_service.execute = MagicMock(
        return_value=asyncio.sleep(0, result={"ok": True})
    )
    asyncio.run(api.execute_tool("t1"))


@pytest.mark.parametrize(
    "call,resource,verb",
    [
        (lambda a: a.get_tool("u1"), "tools", "get"),
        (lambda a: a.list_tools(), "tools", "list"),
        (lambda a: a.get_tool_module("u1"), "tools", "get"),
        (lambda a: a.update_tool_module("u1", "x"), "tools", "update"),
        (lambda a: a.create_tool({}, b"", "m.py"), "tools", "create"),
        (lambda a: a.update_tool("u1", {}), "tools", "update"),
        (lambda a: a.delete_tool("u1"), "tools", "delete"),
        (lambda a: a.create_skill({}), "skills", "create"),
        (lambda a: a.get_skill("u1"), "skills", "get"),
        (lambda a: a.list_skills(), "skills", "list"),
        (lambda a: a.update_skill("u1", {}), "skills", "update"),
        (lambda a: a.update_skill_metadata("u1", {}), "skills", "update"),
        (lambda a: a.delete_skill("u1"), "skills", "delete"),
        (lambda a: a.get_snippet("u1"), "snippets", "get"),
        (lambda a: a.list_snippets(), "snippets", "list"),
        (lambda a: a.create_snippet({}), "snippets", "create"),
        (lambda a: a.update_snippet("u1", {}), "snippets", "update"),
        (lambda a: a.update_snippet_tags("u1", []), "snippets", "update"),
        (lambda a: a.create_vmcp({}), "vmcp_servers", "create"),
        (lambda a: a.get_vmcp("u1"), "vmcp_servers", "get"),
        (lambda a: a.list_vmcps(), "vmcp_servers", "list"),
        (lambda a: a.start_vmcp("u1"), "vmcp_servers", "execute"),
        (lambda a: a.delete_vmcp("u1"), "vmcp_servers", "delete"),
    ],
)
def test_every_named_method_is_admitted_on_its_own_pair(call, resource, verb):
    """Each method must consult the PDP on the pair it claims, and only that
    pair: granting exactly it admits, granting everything else denies."""
    granting = _api(_standalone(verbs=[verb], resources=[resource]))
    set_current_subject(Subject(tenant_id="owner"))
    call(granting)  # must not raise

    other_verb = "delete" if verb != "delete" else "get"
    withholding = _api(_standalone(verbs=[other_verb], resources=[resource]))
    set_current_subject(Subject(tenant_id="owner"))
    with pytest.raises(PluginAuthorizationError):
        call(withholding)


# ── the escape hatch beside the named methods (§2.4) ────────────────────── #


@pytest.mark.parametrize("name", ["tools", "skills", "snippets"])
def test_raw_handler_properties_are_refused_under_acl(name):
    """They reach write_dict, write_file and the locks without passing
    _admit — enforcement point 2 would report full coverage while an
    out-of-tree plugin bypassed it entirely."""
    api = _api(_standalone(verbs=["*"]))
    set_current_subject(Subject(tenant_id="owner"))
    with pytest.raises(PluginAuthorizationError) as exc:
        getattr(api, name)
    assert "unavailable while access control is enabled" in str(exc.value)


# ── §9.1: the framework records the outcome ─────────────────────────────── #


def test_denial_records_an_error_outcome_on_the_object():
    services = _services({"u1": {"uuid": "u1", "tags": ["sast:clean"]}})
    api = _api(_standalone(verbs=["get"]), services, slug="sast")
    set_current_subject(Subject(tenant_id="owner"))
    with pytest.raises(PluginAuthorizationError):
        api.update_skill_tags("u1", ["x"])

    obj = services["_store"]["u1"]
    assert outcome_tag("sast", OUTCOME_ERROR) in obj["tags"]
    assert obj["extra"]["sast"]["outcome"]["state"] == OUTCOME_ERROR
    assert "no role grants" in obj["extra"]["sast"]["outcome"]["reason"]
    # The plugin's own result tag is untouched.
    assert "sast:clean" in obj["tags"]


def test_missing_identity_records_an_error_outcome():
    """The two states most worth recording are exactly the two a plugin cannot
    record for itself — a denied plugin cannot write, and one with no tenant
    cannot write anything at all."""
    services = _services({"u1": {"uuid": "u1", "tags": []}})
    api = _api(_standalone(verbs=["update"]), services, slug="sast")
    with pytest.raises(PluginIdentityError):
        api.update_skill_tags("u1", ["x"])
    obj = services["_store"]["u1"]
    assert outcome_tag("sast", OUTCOME_ERROR) in obj["tags"]
    assert "no tenant in context" in obj["extra"]["sast"]["outcome"]["reason"]


def test_record_outcome_writes_through_the_handler_not_the_service():
    """Going through ``StoreAPI.update_skill`` would re-enter the very _admit
    call that just failed; going through the service layer would emit
    ``content_updated`` and re-enter the handler being recorded for (§9.1)."""
    services = _services({"u1": {"uuid": "u1", "tags": []}})
    api = _api(_standalone(verbs=["get"]), services, slug="sast")
    set_current_subject(Subject(tenant_id="owner"))
    with pytest.raises(PluginAuthorizationError):
        api.update_skill_tags("u1", ["x"])

    services["skills"].handler.write_dict.assert_called_once()
    services["skills"].update.assert_not_called()
    services["skills"].create.assert_not_called()


def test_a_later_outcome_replaces_the_earlier_one():
    store = {"u1": {"uuid": "u1", "tags": []}}
    services = _services(store)
    record_outcome(services, "sast", "u1", OUTCOME_ERROR, "denied")
    record_outcome(services, "sast", "u1", OUTCOME_SKIP, "nothing scannable")
    tags = store["u1"]["tags"]
    assert tags.count(outcome_tag("sast", OUTCOME_SKIP)) == 1
    assert outcome_tag("sast", OUTCOME_ERROR) not in tags


def test_outcome_vocabulary_is_closed():
    services = _services({"u1": {"uuid": "u1"}})
    assert RECORDABLE_OUTCOMES == (OUTCOME_SKIP, OUTCOME_ERROR)
    with pytest.raises(ValueError):
        record_outcome(services, "sast", "u1", "result", "not ours to write")


def test_record_outcome_finds_the_object_in_any_content_type():
    store = {"t1": {"uuid": "t1", "tags": []}}
    services = _services()
    services["_store"].update(store)
    assert record_outcome(services, "sast", "t1", OUTCOME_SKIP, "no python") is True
    assert outcome_tag("sast", OUTCOME_SKIP) in services["_store"]["t1"]["tags"]


def test_record_outcome_is_best_effort_when_there_is_nothing_to_label():
    """It runs on the failure path, so it must never raise over the failure it
    is recording."""
    services = _services()
    assert record_outcome(services, "sast", None, OUTCOME_ERROR, "no uuid") is False
    assert record_outcome(services, None, "u1", OUTCOME_ERROR, "no slug") is False
    assert record_outcome(services, "sast", "gone", OUTCOME_ERROR, "missing") is False


def test_record_outcome_survives_a_failing_write():
    services = _services({"u1": {"uuid": "u1", "tags": []}})
    services["skills"].handler.write_dict.side_effect = OSError("disk full")
    assert record_outcome(services, "sast", "u1", OUTCOME_ERROR, "denied") is False


# ── the undeclared property record_outcome depends on (§2.4) ─────────────── #


@pytest.mark.parametrize(
    "call,service_key",
    [
        (lambda a: a.update_skill("u1", {}), "skills"),
        (lambda a: a.update_tool("u1", {}), "tools"),
        (lambda a: a.update_snippet("u1", {}), "snippets"),
        (lambda a: a.update_skill_tags("u1", ["t"]), "skills"),
        (lambda a: a.update_tool_tags("u1", ["t"]), "tools"),
        (lambda a: a.update_snippet_tags("u1", ["t"]), "snippets"),
        (lambda a: a.update_skill_metadata("u1", {"k": 1}), "skills"),
        (lambda a: a.update_tool_metadata("u1", {"k": 1}), "tools"),
    ],
)
def test_annotation_writes_do_not_re_enter_event_handlers(
    monkeypatch, call, service_key
):
    """These write through ``handler.write_dict``, bypassing the service layer
    where ``emit_content_updated`` lives — so a plugin annotating an object does
    not re-enter its own handler.

    ``record_outcome`` depends on exactly this: a service-layer write would emit
    ``content_updated`` and re-enter the very handlers that just failed. It is
    incidental to how those methods are written rather than something either one
    declares, so it is asserted here.
    """
    from skillberry_store.plugins import events as plugin_events

    emitted = []
    monkeypatch.setattr(
        plugin_events,
        "emit_event",
        lambda name, **kw: emitted.append(name),
    )

    services = _services({"u1": {"uuid": "u1", "tags": []}})
    api = _api(DISABLED, services)
    call(api)

    assert services[service_key].handler.write_dict.called
    assert emitted == []

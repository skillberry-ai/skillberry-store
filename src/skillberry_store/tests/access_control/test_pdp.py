"""Unit tests for the PDP truth table."""

from skillberry_store.access_control.config import (
    AccessControlConfig,
    Role,
    RoleBinding,
    Rule,
    Subject as SubjectRef,
)
from skillberry_store.access_control.pdp import Subject, authorize


def _cfg(*, roles, bindings):
    return AccessControlConfig(
        mode="standalone", roles=list(roles), bindings=list(bindings)
    )


def test_allow_via_role():
    cfg = _cfg(
        roles=[
            Role(
                name="reader",
                rules=[Rule(resources=["skills"], verbs=["list", "get"])],
            )
        ],
        bindings=[
            RoleBinding(
                name="b",
                subjects=[SubjectRef(kind="tenant", name="alice")],
                roles=["reader"],
            )
        ],
    )
    d = authorize(Subject(tenant_id="alice"), "skills", "list", cfg)
    assert d.allowed
    assert "reader" in d.reason


def test_deny_no_matching_rule():
    cfg = _cfg(
        roles=[
            Role(
                name="reader",
                rules=[Rule(resources=["skills"], verbs=["list"])],
            )
        ],
        bindings=[
            RoleBinding(
                name="b",
                subjects=[SubjectRef(kind="tenant", name="alice")],
                roles=["reader"],
            )
        ],
    )
    assert not authorize(Subject(tenant_id="alice"), "skills", "delete", cfg).allowed
    assert not authorize(Subject(tenant_id="alice"), "tools", "list", cfg).allowed


def test_wildcard_resource_and_verb():
    cfg = _cfg(
        roles=[Role(name="admin", rules=[Rule(resources=["*"], verbs=["*"])])],
        bindings=[
            RoleBinding(
                name="b",
                subjects=[SubjectRef(kind="tenant", name="root")],
                roles=["admin"],
            )
        ],
    )
    assert authorize(Subject(tenant_id="root"), "anything", "delete", cfg).allowed


def test_multi_role_union():
    cfg = _cfg(
        roles=[
            Role(
                name="reader",
                rules=[Rule(resources=["skills"], verbs=["list"])],
            ),
            Role(
                name="tool-runner",
                rules=[Rule(resources=["tools"], verbs=["execute"])],
            ),
        ],
        bindings=[
            RoleBinding(
                name="b",
                subjects=[SubjectRef(kind="tenant", name="alice")],
                roles=["reader", "tool-runner"],
            )
        ],
    )
    assert authorize(Subject(tenant_id="alice"), "skills", "list", cfg).allowed
    assert authorize(Subject(tenant_id="alice"), "tools", "execute", cfg).allowed
    assert not authorize(Subject(tenant_id="alice"), "tools", "delete", cfg).allowed


def test_group_binding_matches_via_groups():
    cfg = _cfg(
        roles=[Role(name="admin", rules=[Rule(resources=["*"], verbs=["*"])])],
        bindings=[
            RoleBinding(
                name="admins-group",
                subjects=[SubjectRef(kind="group", name="admins")],
                roles=["admin"],
            )
        ],
    )
    subject = Subject(tenant_id="bob", groups=["admins"])
    assert authorize(subject, "skills", "delete", cfg).allowed


def test_empty_bindings_denies_everything():
    cfg = _cfg(roles=[], bindings=[])
    assert not authorize(Subject(tenant_id="alice"), "skills", "list", cfg).allowed

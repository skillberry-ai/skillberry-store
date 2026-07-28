"""Unit tests for the per-tenant MCP surface planner."""

from fastapi import FastAPI

from skillberry_store.access_control.config import (
    AccessControlConfig,
    Role,
    RoleBinding,
    Rule,
    Subject as SubjectRef,
    User,
)
from skillberry_store.access_control.mcp_plan import (
    operations_for_subject,
    operations_for_user,
)
from skillberry_store.access_control.pdp import Subject


def _app_with_mcp_marked_routes() -> FastAPI:
    app = FastAPI()

    @app.get(
        "/skills/",
        tags=["skills"],
        operation_id="list_skills",
        openapi_extra={"x-mcp-tool": True},
    )
    def list_skills():
        return []

    @app.post(
        "/skills/",
        tags=["skills"],
        operation_id="create_skill",
        openapi_extra={"x-mcp-tool": True},
    )
    def create_skill():
        return {}

    @app.delete(
        "/skills/{uuid_or_name}",
        tags=["skills"],
        operation_id="delete_skill",
        openapi_extra={"x-mcp-tool": True},
    )
    def delete_skill(uuid_or_name: str):
        return {}

    @app.post(
        "/tools/{uuid_or_name}/execute",
        tags=["tools"],
        operation_id="execute_tool",
        openapi_extra={"x-mcp-tool": True},
    )
    def execute_tool(uuid_or_name: str):
        return {}

    # Not opted in — must never appear in an MCP surface regardless of RBAC.
    @app.get(
        "/facets/skills",
        tags=["skills"],
        operation_id="skill_facets",
    )
    def facets():
        return {}

    return app


def _cfg_with_roles() -> AccessControlConfig:
    return AccessControlConfig(
        mode="standalone",
        users=[
            User(
                username="alice",
                tenant_id="alice",
                password_hash="$2b$12$x",
                groups=[],
            ),
            User(
                username="bob",
                tenant_id="bob",
                password_hash="$2b$12$x",
                groups=[],
            ),
            User(
                username="root",
                tenant_id="root",
                password_hash="$2b$12$x",
                groups=["admins"],
            ),
        ],
        roles=[
            Role(
                name="reader",
                rules=[
                    Rule(
                        resources=["skills", "tools"],
                        verbs=["list", "get", "search"],
                    )
                ],
            ),
            Role(
                name="content-author",
                rules=[
                    Rule(
                        resources=["skills"],
                        verbs=["list", "get", "create", "update", "delete"],
                    )
                ],
            ),
            Role(
                name="admin",
                rules=[Rule(resources=["*"], verbs=["*"])],
            ),
        ],
        bindings=[
            RoleBinding(
                name="alice-reader",
                subjects=[SubjectRef(kind="tenant", name="alice")],
                roles=["reader"],
            ),
            RoleBinding(
                name="bob-author",
                subjects=[SubjectRef(kind="tenant", name="bob")],
                roles=["content-author"],
            ),
            RoleBinding(
                name="admins-group",
                subjects=[SubjectRef(kind="group", name="admins")],
                roles=["admin"],
            ),
        ],
    )


def test_reader_surface_excludes_writes_and_execute():
    app = _app_with_mcp_marked_routes()
    cfg = _cfg_with_roles()
    ops = operations_for_user(app, cfg.user("alice"), cfg)
    # list_skills yes (list/get on skills); the rest are writes/execute.
    assert "list_skills" in ops
    assert "create_skill" not in ops
    assert "delete_skill" not in ops
    assert "execute_tool" not in ops
    # Non-marked route never appears.
    assert "skill_facets" not in ops


def test_author_surface_includes_create_and_delete():
    app = _app_with_mcp_marked_routes()
    cfg = _cfg_with_roles()
    ops = operations_for_user(app, cfg.user("bob"), cfg)
    assert "create_skill" in ops
    assert "delete_skill" in ops
    assert "list_skills" in ops
    assert "execute_tool" not in ops  # not a tool-runner


def test_admin_surface_includes_everything_marked():
    app = _app_with_mcp_marked_routes()
    cfg = _cfg_with_roles()
    ops = operations_for_user(app, cfg.user("root"), cfg)
    assert set(ops) == {
        "list_skills",
        "create_skill",
        "delete_skill",
        "execute_tool",
    }


def test_anonymous_subject_gets_empty_surface():
    app = _app_with_mcp_marked_routes()
    cfg = _cfg_with_roles()
    ops = operations_for_subject(app, Subject(tenant_id=None), cfg)
    assert ops == []


def test_unmarked_routes_never_included_even_for_admin():
    app = _app_with_mcp_marked_routes()
    cfg = _cfg_with_roles()
    ops = operations_for_user(app, cfg.user("root"), cfg)
    assert "skill_facets" not in ops

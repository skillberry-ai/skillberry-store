"""The sanctioned plugin surface must not hand out unguarded store access.

``skillberry_store.standalone`` is what a plugin may construct and own.
Owning such an instance is code sharing, not an access-control bypass — a
privately constructed sandbox permits nothing ACL governs. The one exception
is ``VirtualMcpServer``'s default tool source: it falls back to the
``ObjectHandler`` singletons plus the service registry, reading manifests
and module files, walking dependencies and executing, entirely outside
``StoreAPI`` and therefore outside admission control (plugin-identity §6.2).
"""

from __future__ import annotations

import pytest

from skillberry_store.access_control import config as acl_config


@pytest.fixture
def acl_mode(monkeypatch, tmp_path):
    """Point the cached ACL loader at a config in the requested mode."""

    def use(mode: str):
        path = tmp_path / "acl.yaml"
        path.write_text(f"mode: {mode}\n")
        monkeypatch.setenv("SBS_ACCESS_CONTROL_CONFIG", str(path))
        acl_config.reset_config_cache()

    yield use
    acl_config.reset_config_cache()


def test_missing_tool_source_is_refused_under_acl(acl_mode):
    from skillberry_store.standalone import VirtualMcpServer

    acl_mode("standalone")
    with pytest.raises(PermissionError) as exc:
        VirtualMcpServer(
            name="twin", description="d", port=None, tools=[], serve=False
        )
    assert "explicit tool_source" in str(exc.value)


def test_the_core_class_keeps_its_fallback(acl_mode):
    """The store's own managed vMCP servers rely on it, and they are created
    through an endpoint the PDP already decided on."""
    import inspect

    from skillberry_store.modules.vmcp_server import VirtualMcpServer as Core

    acl_mode("standalone")
    sig = inspect.signature(Core.__init__)
    assert sig.parameters["tool_source"].default is None


def test_an_injected_tool_source_is_accepted(acl_mode, monkeypatch):
    """``dast``'s benign twin passes a ``StoreApiToolSource``, so it stays
    faithful *and* admitted."""
    import skillberry_store.modules.vmcp_server as vmcp_mod
    from skillberry_store.standalone import VirtualMcpServer

    acl_mode("standalone")
    monkeypatch.setattr(
        vmcp_mod.VirtualMcpServer, "__init__", lambda self, *a, **kw: None
    )
    source = object()
    server = VirtualMcpServer(
        name="twin", description="d", port=None, tools=[], serve=False,
        tool_source=source,
    )
    assert isinstance(server, VirtualMcpServer)


def test_disabled_mode_keeps_the_default_source(acl_mode, monkeypatch):
    import skillberry_store.modules.vmcp_server as vmcp_mod
    from skillberry_store.standalone import VirtualMcpServer

    acl_mode("disabled")
    monkeypatch.setattr(
        vmcp_mod.VirtualMcpServer, "__init__", lambda self, *a, **kw: None
    )
    VirtualMcpServer(name="twin", description="d", port=None, tools=[], serve=False)


def test_file_executor_needs_no_such_treatment():
    """It takes its source as an input, which the caller obtained through
    ``StoreAPI`` in the first place."""
    import inspect

    from skillberry_store.standalone import FileExecutor

    params = inspect.signature(FileExecutor.__init__).parameters
    assert "file_content" in params

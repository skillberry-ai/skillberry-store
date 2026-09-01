"""Coverage for VirtualMcpServer's standalone (injected-source) mode.

A caller that owns its own server instance must be able to construct one
without the core server's process-global state: no ``ObjectHandler``
singletons, no service registry, no shared port range, and no entries in the
process-wide metric series. These tests assert that — the singleton accessors
are poisoned so that touching them fails loudly rather than silently working
because an earlier test initialised them.
"""

import threading
from unittest.mock import MagicMock, patch

import pytest

from skillberry_store.modules import vmcp_server as vmcp_mod
from skillberry_store.modules.vmcp_server import InvokeRecord, VirtualMcpServer

TOOL_A = {
    "uuid": "uuid-a",
    "name": "alpha",
    "module_name": "alpha.py",
    "packaging_format": "code",
    "programming_language": "python",
    "params": {"type": "object", "properties": {}, "required": []},
}
TOOL_B = {
    "uuid": "uuid-b",
    "name": "beta",
    "module_name": "beta.py",
    "packaging_format": "code",
    "programming_language": "python",
    "params": {"type": "object", "properties": {}, "required": []},
}


class FakeToolSource:
    """A ToolSource backed by a dict — no store, no filesystem, no registry."""

    def __init__(self, tools=None, result=None, error=None):
        self._tools = {t["uuid"]: t for t in (tools or [TOOL_A, TOOL_B])}
        self._result = result if result is not None else {"return value": "ok"}
        self._error = error
        self.executed = []

    def get_manifest(self, uuid):
        return dict(self._tools[uuid])

    async def execute(self, manifest, parameters, env_id):
        self.executed.append((manifest.get("name"), parameters, env_id))
        if self._error is not None:
            raise self._error
        return self._result


@pytest.fixture(autouse=True)
def _poison_singletons(monkeypatch):
    """Fail loudly if standalone construction reaches for core singletons."""

    def _forbidden(*args, **kwargs):  # pragma: no cover - only on regression
        raise AssertionError("standalone server must not touch core singletons")

    monkeypatch.setattr(vmcp_mod, "get_object_handler", _forbidden)
    import skillberry_store.services.registry as registry_mod

    monkeypatch.setattr(registry_mod, "get_service", _forbidden)


def _server(source=None, **kwargs):
    kwargs.setdefault("metrics_enabled", False)
    return VirtualMcpServer(
        name="standalone-test",
        description="",
        port=None,
        tools=["uuid-a", "uuid-b"],
        tool_source=source or FakeToolSource(),
        serve=False,
        **kwargs,
    )


# ── construction ──────────────────────────────────────────────────────────────


def test_manifests_load_without_any_singletons():
    server = _server()
    assert server.tool_names() == ["alpha", "beta"]
    assert server.tool_manifest("alpha")["uuid"] == "uuid-a"
    assert server.tool_manifest("absent") is None


def test_serve_false_takes_no_port_and_starts_no_thread():
    """No transport means nothing to leak: no port held, no uvicorn thread."""
    before = set(threading.enumerate())

    server = _server()

    assert server.port is None
    assert server.mcp is None
    assert getattr(server, "server_thread", None) is None
    assert set(threading.enumerate()) == before


def test_stop_is_a_noop_without_a_transport():
    server = _server()
    server.stop()  # must not raise


def test_context_manager_stops_the_server():
    with _server() as server:
        assert server.tool_names()


def test_unresolvable_tool_is_skipped_not_fatal():
    class PartialSource(FakeToolSource):
        def get_manifest(self, uuid):
            if uuid == "uuid-b":
                raise KeyError("gone")
            return super().get_manifest(uuid)

    server = _server(source=PartialSource())
    assert server.tool_names() == ["alpha"]


def test_manifest_without_a_name_is_skipped():
    source = FakeToolSource(tools=[TOOL_A, {"uuid": "uuid-b"}])
    server = _server(source=source)
    assert server.tool_names() == ["alpha"]


def test_list_tools_maps_manifests_to_mcp_tools():
    tools = _server().list_tools()
    assert sorted(t.name for t in tools) == ["alpha", "beta"]


def test_list_tools_skips_a_manifest_it_cannot_convert():
    """A manifest missing ``params`` must not take out the whole listing."""
    broken = {"uuid": "uuid-b", "name": "beta", "module_name": "beta.py"}
    server = _server(source=FakeToolSource(tools=[TOOL_A, broken]))

    tools = server.list_tools()

    assert [t.name for t in tools] == ["alpha"]
    # still registered for dispatch, even though it has no MCP schema
    assert server.tool_names() == ["alpha", "beta"]


# ── dispatch ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invoke_tool_delegates_to_the_source():
    source = FakeToolSource()
    server = _server(source=source)

    result = await server.invoke_tool("alpha", {"x": 1}, "env-1")

    assert result == {"return value": "ok"}
    assert source.executed == [("alpha", {"x": 1}, "env-1")]


@pytest.mark.asyncio
async def test_invoke_tool_passes_the_pinned_manifest():
    """Dispatch uses the manifest captured at registration, not a fresh read."""
    source = FakeToolSource()
    server = _server(source=source)
    source._tools["uuid-a"] = dict(TOOL_A, name="alpha", module_name="swapped.py")

    await server.invoke_tool("alpha", {}, "")

    assert server.tool_manifest("alpha")["module_name"] == "alpha.py"


@pytest.mark.asyncio
async def test_invoke_unknown_tool_raises():
    with pytest.raises(ValueError, match="not found"):
        await _server().invoke_tool("nope", {}, "")


# ── observation hook ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_on_invoke_records_success():
    seen = []
    server = _server(on_invoke=seen.append)

    await server.invoke_tool("alpha", {"x": 1}, "")

    assert len(seen) == 1
    record = seen[0]
    assert isinstance(record, InvokeRecord)
    assert record.tool_name == "alpha"
    assert record.parameters == {"x": 1}
    assert record.result == {"return value": "ok"}
    assert record.failed is False


@pytest.mark.asyncio
async def test_on_invoke_records_failure():
    """A raising tool must still be observed — those are the interesting calls."""
    seen = []
    boom = RuntimeError("boom")
    server = _server(source=FakeToolSource(error=boom), on_invoke=seen.append)

    with pytest.raises(RuntimeError):
        await server.invoke_tool("alpha", {"x": 1}, "")

    assert len(seen) == 1
    assert seen[0].failed is True
    assert seen[0].error is boom
    assert seen[0].result is None


@pytest.mark.asyncio
async def test_a_throwing_hook_does_not_break_dispatch():
    def _bad_hook(record):
        raise ValueError("observer is broken")

    server = _server(on_invoke=_bad_hook)

    assert await server.invoke_tool("alpha", {}, "") == {"return value": "ok"}


@pytest.mark.asyncio
async def test_a_throwing_hook_does_not_mask_the_original_error():
    def _bad_hook(record):
        raise ValueError("observer is broken")

    server = _server(source=FakeToolSource(error=RuntimeError("boom")),
                     on_invoke=_bad_hook)

    with pytest.raises(RuntimeError, match="boom"):
        await server.invoke_tool("alpha", {}, "")


# ── metrics ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_metrics_disabled_records_nothing():
    """Throwaway server names must not accumulate Prometheus label cardinality."""
    server = _server()

    with patch.object(vmcp_mod, "invoke_vmcp_tool_counter") as attempted, patch.object(
        vmcp_mod, "invoke_successfully_vmcp_tool_counter"
    ) as succeeded:
        await server.invoke_tool("alpha", {}, "")

    attempted.labels.assert_not_called()
    succeeded.labels.assert_not_called()


@pytest.mark.asyncio
async def test_metrics_enabled_records_both_counters():
    server = _server(metrics_enabled=True)

    with patch.object(vmcp_mod, "invoke_vmcp_tool_counter") as attempted, patch.object(
        vmcp_mod, "invoke_successfully_vmcp_tool_counter"
    ) as succeeded, patch.object(vmcp_mod, "invoke_successfully_vmcp_tool_latency"):
        await server.invoke_tool("alpha", {}, "")

    attempted.labels.assert_called_once_with(
        server_name="standalone-test", tool_name="alpha"
    )
    succeeded.labels.assert_called_once_with(
        server_name="standalone-test", tool_name="alpha"
    )


# ── default (in-process) source ────────────────────────────────────────────────


def test_default_source_still_uses_the_core_handler(monkeypatch):
    """Passing no source must behave exactly as before: core singletons."""
    handler = MagicMock()
    handler.read_dict.return_value = TOOL_A
    monkeypatch.setattr(vmcp_mod, "get_object_handler", lambda _name: handler)

    source = vmcp_mod._HandlerToolSource()

    assert source.get_manifest("uuid-a")["name"] == "alpha"
    handler.read_dict.assert_called_once_with("uuid-a")


@pytest.mark.asyncio
async def test_default_source_assembles_dependencies_via_the_service(monkeypatch):
    """The in-process path keeps using the store's own transitive-closure walk."""
    handler = MagicMock()
    handler.read_file.return_value = "def alpha(): pass"
    handler.read_dicts.return_value = [
        {"uuid": "dep-1", "name": "dep", "module_name": "dep.py"}
    ]
    tools_service = MagicMock()
    tools_service.find_dependencies.return_value = {"dep-1"}

    import skillberry_store.services.registry as registry_mod

    monkeypatch.setattr(registry_mod, "get_service", lambda _t: tools_service)

    source = vmcp_mod._HandlerToolSource(handler=handler)
    manifest = dict(TOOL_A, dependencies=["dep-1"])

    with patch.object(vmcp_mod, "FastMCP"), patch(
        "skillberry_store.modules.file_executor.FileExecutor.execute_file"
    ) as execute_file:
        execute_file.return_value = {"return value": "ok"}
        result = await source.execute(manifest, {"x": 1}, "env-1")

    assert result == {"return value": "ok"}
    tools_service.find_dependencies.assert_called_once_with(["dep-1"], "uuid-a")


@pytest.mark.asyncio
async def test_default_source_rejects_manifest_without_module_name(monkeypatch):
    handler = MagicMock()
    source = vmcp_mod._HandlerToolSource(handler=handler)

    with pytest.raises(ValueError, match="no module_name"):
        await source.execute({"uuid": "uuid-a", "name": "alpha"}, {}, "")


@pytest.mark.asyncio
async def test_default_source_rejects_manifest_without_uuid():
    handler = MagicMock()
    source = vmcp_mod._HandlerToolSource(handler=handler)

    with pytest.raises(ValueError, match="no uuid"):
        await source.execute({"name": "alpha", "module_name": "a.py"}, {}, "")


def test_standalone_surface_reexports_the_server():
    from skillberry_store.standalone import VirtualMcpServer as Exported

    assert Exported is VirtualMcpServer

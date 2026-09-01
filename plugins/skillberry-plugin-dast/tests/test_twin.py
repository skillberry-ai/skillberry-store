"""Tests for the benign vMCP twin and its StoreAPI-backed tool source.

The twin previously had no coverage at all, which is how it shipped registering
**zero** tools: it constructed a VirtualMcpServer without a FastAPI app, so the
server fell back to fetching manifests over HTTP with ``narrow`` field
selection, every manifest lacked ``params``, and each tool was silently dropped.
Since ``DAST_SCOPE`` defaults to ``mcp``, that made the default live scan a
no-op. ``test_twin_registers_tools`` is the regression guard.

No transport is started (``serve=False``) so these run in-process with no port
and no uvicorn thread.
"""

import pytest

from skillberry_plugin_dast.engine.tool_source import StoreApiToolSource
from skillberry_plugin_dast.engine.twin import BenignMcpTwin

TOOL = {
    "uuid": "t1",
    "name": "send",
    "module_name": "s.py",
    "packaging_format": "code",
    "programming_language": "python",
    "params": {"properties": {"p": {"type": "string"}}, "required": ["p"]},
}


class FakeStore:
    """The slice of StoreAPI the tool source uses."""

    def __init__(self, tools=None, result=None, error=None):
        self._tools = {t["uuid"]: t for t in (tools or [TOOL])}
        self._result = result if result is not None else {"return value": "ok"}
        self._error = error
        self.executed = []

    def get_tool(self, uuid):
        return dict(self._tools[uuid]) if uuid in self._tools else None

    async def execute_tool(self, uuid, parameters, env_id=""):
        self.executed.append((uuid, parameters, env_id))
        if self._error is not None:
            raise self._error
        return self._result


def _twin(store=None, uuids=("t1",)):
    store = store or FakeStore()
    return BenignMcpTwin(
        name="dast-twin-test",
        tool_uuids=list(uuids),
        tool_source=StoreApiToolSource(store),
    )


# ── registration (the zero-tools regression) ──────────────────────────────────


def test_twin_registers_tools():
    """Regression: the twin must actually serve the skill's tools.

    A twin that registers nothing makes Scope A — the default scope — silently
    exercise nothing at all.
    """
    twin = _twin().start()
    try:
        assert twin.tool_names() == ["send"]
    finally:
        twin.stop()


def test_tool_names_empty_before_start():
    assert _twin().tool_names() == []


def test_tool_names_empty_after_stop():
    twin = _twin().start()
    twin.stop()
    assert twin.tool_names() == []


def test_twin_takes_no_port_and_starts_no_thread():
    import threading

    before = set(threading.enumerate())
    twin = _twin().start()
    try:
        assert twin._server.port is None
        assert set(threading.enumerate()) == before
    finally:
        twin.stop()


def test_unknown_tool_uuid_is_skipped():
    twin = _twin(uuids=("t1", "missing")).start()
    try:
        assert twin.tool_names() == ["send"]
    finally:
        twin.stop()


# ── observation ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_drive_tool_records_the_call():
    store = FakeStore()
    twin = _twin(store=store).start()
    try:
        result = await twin.drive_tool("send", {"p": "x"})
    finally:
        twin.stop()

    assert result == {"return value": "ok"}
    assert store.executed == [("t1", {"p": "x"}, "")]
    assert twin.calls == [
        {"tool": "send", "args": {"p": "x"}, "result_excerpt": "{'return value': 'ok'}"}
    ]


@pytest.mark.asyncio
async def test_drive_tool_records_failures_too():
    """A tool that raises under adversarial input is the interesting case."""
    twin = _twin(store=FakeStore(error=RuntimeError("boom"))).start()
    try:
        with pytest.raises(RuntimeError):
            await twin.drive_tool("send", {"p": "x"})
    finally:
        twin.stop()

    assert len(twin.calls) == 1
    assert twin.calls[0]["tool"] == "send"
    assert "boom" in twin.calls[0]["error"]


@pytest.mark.asyncio
async def test_result_excerpt_is_truncated():
    twin = _twin(store=FakeStore(result={"return value": "y" * 1000})).start()
    try:
        await twin.drive_tool("send", {"p": "x"})
    finally:
        twin.stop()

    assert len(twin.calls[0]["result_excerpt"]) == 300


@pytest.mark.asyncio
async def test_drive_tool_before_start_raises():
    with pytest.raises(RuntimeError, match="not started"):
        await _twin().drive_tool("send", {})


def test_stop_is_idempotent():
    twin = _twin().start()
    twin.stop()
    twin.stop()


# ── the StoreAPI-backed source ────────────────────────────────────────────────


def test_source_get_manifest_returns_full_tool():
    source = StoreApiToolSource(FakeStore())
    assert source.get_manifest("t1")["name"] == "send"


def test_source_get_manifest_raises_for_missing_tool():
    """The server treats a KeyError as "skip this tool", not as fatal."""
    with pytest.raises(KeyError):
        StoreApiToolSource(FakeStore()).get_manifest("nope")


@pytest.mark.asyncio
async def test_source_executes_through_store_api():
    """Execution goes through the store's own path, not a locally built bundle."""
    store = FakeStore()
    source = StoreApiToolSource(store)

    result = await source.execute(TOOL, {"p": "x"}, "env-1")

    assert result == {"return value": "ok"}
    assert store.executed == [("t1", {"p": "x"}, "env-1")]


@pytest.mark.asyncio
async def test_source_rejects_manifest_without_uuid():
    source = StoreApiToolSource(FakeStore())
    with pytest.raises(ValueError, match="no uuid"):
        await source.execute({"name": "send"}, {}, "")

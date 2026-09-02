"""Coverage for FileExecutor's dispatch resolution and synchronous entry point.

``execute_file_sync`` exists for callers that manage their own threading and
must be able to abandon a hung execution — ``asyncio.to_thread``'s pool threads
are non-daemon and joined at interpreter exit, so work offloaded there cannot be
walked away from. Both entry points share ``_resolve_path`` so they cannot
disagree about which backend a manifest selects.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from skillberry_store.modules.file_executor import FileExecutor

ADD_SOURCE = """
def add(a: int, b: int) -> int:
    '''Adds two numbers.

    Args:
        a (int): first.
        b (int): second.

    Returns:
        int: the sum.
    '''
    return a + b
"""


def _executor(*, language="python", packaging="code", locally=True, name="add"):
    return FileExecutor(
        name=name,
        file_content=ADD_SOURCE,
        file_manifest={
            "name": name,
            "module_name": f"{name}.py",
            "programming_language": language,
            "packaging_format": packaging,
        },
        execute_python_locally=locally,
    )


# ── _resolve_path ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "language,packaging,locally,expected",
    [
        ("python", "code", True, FileExecutor.PATH_PYTHON_LOCAL),
        ("python", "code", False, FileExecutor.PATH_PYTHON_DOCKER),
        ("python", "mcp", True, FileExecutor.PATH_MCP),
        ("bash", "code", True, FileExecutor.PATH_BASH),
    ],
    ids=["python_local", "python_docker", "mcp", "bash"],
)
def test_resolve_path_covers_every_backend(language, packaging, locally, expected):
    ex = _executor(language=language, packaging=packaging, locally=locally)
    assert ex._resolve_path() == expected


def test_resolve_path_reads_locally_flag_dynamically():
    """The flag may be flipped after construction; dispatch must follow."""
    ex = _executor(locally=False)
    assert ex._resolve_path() == FileExecutor.PATH_PYTHON_DOCKER
    ex.execute_python_locally = True
    assert ex._resolve_path() == FileExecutor.PATH_PYTHON_LOCAL


def test_resolve_path_rejects_unknown_language():
    ex = _executor(language="rust")
    with pytest.raises(HTTPException) as exc:
        ex._resolve_path()
    assert exc.value.status_code == 400
    assert "programming language" in exc.value.detail


def test_resolve_path_rejects_unknown_packaging():
    ex = _executor(packaging="wheel")
    with pytest.raises(HTTPException) as exc:
        ex._resolve_path()
    assert exc.value.status_code == 400
    assert "packaging format" in exc.value.detail


# ── execute_file_sync ─────────────────────────────────────────────────────────


def test_sync_and_async_agree_for_local_python():
    """The two entry points must produce identical results for the same input."""
    import asyncio

    sync_result = _executor().execute_file_sync({"a": 5, "b": 8})
    async_result = asyncio.run(_executor().execute_file({"a": 5, "b": 8}))

    assert sync_result["return value"] == "13"
    assert sync_result == async_result


def test_sync_dispatches_to_docker_when_not_local():
    ex = _executor(locally=False)
    with patch.object(
        ex, "execute_python_file_using_docker", return_value={"return value": "ok"}
    ) as docker:
        assert ex.execute_file_sync({"a": 1}, env_id="e") == {"return value": "ok"}
    docker.assert_called_once_with({"a": 1}, env_id="e")


def test_sync_dispatches_to_bash():
    ex = _executor(language="bash")
    with patch.object(
        ex, "execute_bash_file", return_value={"return value": "ok"}
    ) as bash:
        assert ex.execute_file_sync({"a": 1}) == {"return value": "ok"}
    bash.assert_called_once_with(parameters={"a": 1})


def test_sync_drives_the_mcp_path_on_a_private_loop():
    """MCP is natively async; the sync entry point still has to serve it."""
    ex = _executor(packaging="mcp")

    async def _fake(parameters):
        return {"return value": f"mcp:{parameters}"}

    with patch.object(ex, "execute_python_file_in_mcp_server", _fake):
        assert ex.execute_file_sync({"a": 1}) == {"return value": "mcp:{'a': 1}"}


def test_sync_reports_backend_failure_as_error_dict():
    ex = _executor()
    with patch.object(
        ex, "execute_python_file_locally", side_effect=RuntimeError("boom")
    ):
        result = ex.execute_file_sync({"a": 1})
    assert "boom" in result["error"]


def test_sync_propagates_http_exception():
    """A 400 from dispatch is a caller error and must not be flattened."""
    ex = _executor(language="rust")
    with pytest.raises(HTTPException):
        ex.execute_file_sync({"a": 1})


# ── execute_file delegation ───────────────────────────────────────────────────


def test_async_keeps_mcp_on_the_callers_loop():
    """The MCP session must not be moved to a worker thread's loop."""
    import asyncio

    ex = _executor(packaging="mcp")
    seen = {}

    async def _fake(parameters):
        seen["loop"] = asyncio.get_running_loop()
        return {"return value": "ok"}

    async def _run():
        with patch.object(ex, "execute_python_file_in_mcp_server", _fake):
            result = await ex.execute_file({"a": 1})
        return result, asyncio.get_running_loop()

    result, caller_loop = asyncio.run(_run())
    assert result == {"return value": "ok"}
    assert seen["loop"] is caller_loop


def test_async_offloads_blocking_paths_to_a_worker_thread():
    import asyncio
    import threading

    ex = _executor()
    seen = {}

    def _fake(parameters, env_id=None):
        seen["thread"] = threading.current_thread()
        return {"return value": "ok"}

    async def _run():
        with patch.object(ex, "execute_python_file_locally", _fake):
            return await ex.execute_file({"a": 1})

    assert asyncio.run(_run()) == {"return value": "ok"}
    assert seen["thread"] is not threading.main_thread()


def test_standalone_surface_reexports_file_executor():
    """Plugins import from ``standalone``, not from ``modules``."""
    from skillberry_store.standalone import FileExecutor as Exported

    assert Exported is FileExecutor

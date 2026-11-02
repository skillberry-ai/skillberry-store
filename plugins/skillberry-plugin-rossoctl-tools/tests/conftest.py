import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from rossoctl_fake_backend import BACKEND, TOKEN_URL, FakeRossoctl  # noqa: E402


@pytest.fixture
def fake():
    return FakeRossoctl()


@pytest.fixture
def backend(fake):
    from skillberry_plugin_rossoctl_tools.backend import RossoctlBackend

    return RossoctlBackend(
        base_url=BACKEND,
        client_id="skillberry-store-tools",
        client_secret="s3cret",
        token_endpoint=TOKEN_URL,
        allowed_namespaces=[],
        timeout=5,
        transport=fake.transport(),
    )


@pytest.fixture
def store_client(fake, backend, tmp_path, monkeypatch):
    """A full in-process store with the plugin active, wired to the fake backend.

    The plugin is constructed by the real loader (entry point discovery); its
    backend is then pointed at the fake. Plugin config enables only the
    plugins this test needs.
    """
    from fastapi.testclient import TestClient

    from skillberry_store.access_control import config as acl_config
    from skillberry_store.fast_api.server import SBS
    from skillberry_store.modules import object_handler
    from skillberry_store.services import registry

    monkeypatch.setenv("SBS_BASE_DIR", str(tmp_path / "sbs"))
    monkeypatch.setenv("ROSSOCTL_BACKEND_URL", BACKEND)
    monkeypatch.setenv("PROMETHEUS_METRICS_PORT", "0")
    monkeypatch.setenv("SBS_ACCESS_CONTROL_CONFIG", str(tmp_path / "acl.yaml"))
    (tmp_path / "acl.yaml").write_text("mode: disabled\n")
    plugin_cfg = tmp_path / "plugins.json"
    plugin_cfg.write_text(json.dumps({"disabled": [], "owners": {}}))
    monkeypatch.setenv("SKILLBERRY_PLUGIN_CONFIG", str(plugin_cfg))
    # The registries are process-global and may already back a session-wide
    # server (the root conftest's ``run_sbs``); snapshot and restore them so
    # this in-process store does not leave that server without services.
    saved = (
        dict(object_handler._object_handlers),
        object_handler._initialized,
        dict(registry._services),
        registry._initialized,
        acl_config._config_cache,
        acl_config._config_path_loaded,
    )
    acl_config.reset_config_cache()
    object_handler.clear_object_handlers()
    registry.clear_services()
    app = SBS()
    plugin = app.state.plugin_loader.plugins["rossoctl-tools"]
    plugin.backend = backend
    client = TestClient(app)
    client.plugin = plugin
    client.loader = app.state.plugin_loader
    yield client
    object_handler.clear_object_handlers()
    registry.clear_services()
    object_handler._object_handlers.update(saved[0])
    object_handler._initialized = saved[1]
    registry._services.update(saved[2])
    registry._initialized = saved[3]
    acl_config._config_cache, acl_config._config_path_loaded = saved[4], saved[5]


@pytest.fixture
def served_fake(fake, monkeypatch):
    """The fake backend on a real local port, for code that uses urllib.

    The proxy tools run inside core's executor (local mode) and reach rossoctl
    with the standard library, not through the plugin's httpx transport. This
    serves the same fake app and points ROSSOCTL_BACKEND_URL / the token
    endpoint at it, so store-side Execute goes through its /invoke.
    """
    import socket
    import threading
    import time

    import uvicorn

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(fake.app, host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 15
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    base = f"http://127.0.0.1:{port}"
    monkeypatch.setenv("ROSSOCTL_BACKEND_URL", base)
    monkeypatch.setenv("ROSSOCTL_CLIENT_ID", "skillberry-store-tools")
    monkeypatch.setenv("ROSSOCTL_CLIENT_SECRET", "s3cret")
    monkeypatch.setenv(
        "ROSSOCTL_TOKEN_ENDPOINT",
        f"{base}/realms/rossoctl/protocol/openid-connect/token",
    )
    monkeypatch.setenv("EXECUTE_PYTHON_LOCALLY", "true")
    yield base
    server.should_exit = True
    thread.join(timeout=5)

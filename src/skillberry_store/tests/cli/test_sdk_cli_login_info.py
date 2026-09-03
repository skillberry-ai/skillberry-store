# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0
"""Coverage for ``sbs login``'s preflight probe and the login message.

``skillberry-common/scripts/sdk_cli.py`` is the generation template that
``make generate-sdk`` substitutes ``{{API_NAME}}`` / ``{{API_URL}}`` into, so
it cannot simply be imported. The fixture below does the substitution into a
temp file and imports that as a module — the same text that ships in the SDK.

What is under test (§7 and §12.5 of docs/design/login-info.md):

* ``_preflight`` returns two facts from the one request ``sbs login`` already
  makes, and never raises.
* the message is printed to **stderr**, exactly once, before the first prompt.
* every failure shape degrades to today's behavior with no traceback.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

TEMPLATE = (
    Path(__file__).resolve().parents[4]
    / "skillberry-common"
    / "scripts"
    / "sdk_cli.py"
)


@pytest.fixture(scope="module")
def sdk_cli(tmp_path_factory):
    """Import the generation template with its placeholders substituted."""
    assert TEMPLATE.is_file(), f"CLI template missing at {TEMPLATE}"
    source = (
        TEMPLATE.read_text()
        .replace("{{API_NAME}}", "sbs")
        .replace("{{API_URL}}", "http://127.0.0.1:1")
    )
    path = tmp_path_factory.mktemp("sdk_cli") / "sdk_cli_under_test.py"
    path.write_text(source)

    spec = importlib.util.spec_from_file_location("sdk_cli_under_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop(spec.name, None)


@pytest.fixture
def stub_server():
    """Serve one canned response for ``GET /auth/whoami``.

    ``start(status, body)`` — ``body`` may be a dict (serialised as JSON) or
    raw bytes, so a non-JSON body can be exercised too. Returns the base URL.
    """
    servers = []

    def start(status: int, body) -> str:
        payload = (
            body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        )

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler's API
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass  # keep pytest output clean

        server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return f"http://127.0.0.1:{server.server_port}"

    yield start
    for server in servers:
        server.shutdown()
        server.server_close()


MESSAGE = "Shared eval box — do not store secrets."


# --------------------------------------------------------------------------- #
# _preflight
# --------------------------------------------------------------------------- #

def test_401_with_a_message_returns_it(sdk_cli, stub_server):
    url = stub_server(401, {"detail": "missing_authorization", "login_info": MESSAGE})

    assert sdk_cli._preflight(url) == (False, MESSAGE)


def test_401_without_a_message_returns_none(sdk_cli, stub_server):
    """An older server, or one with no message configured."""
    url = stub_server(401, {"detail": "missing_authorization"})

    assert sdk_cli._preflight(url) == (False, None)


def test_503_auth_disabled_is_still_detected(sdk_cli, stub_server):
    """The pre-existing fact must survive the probe growing a second one."""
    url = stub_server(503, {"detail": "auth_disabled"})

    assert sdk_cli._preflight(url) == (True, None)


def test_503_with_another_detail_is_not_auth_disabled(sdk_cli, stub_server):
    url = stub_server(503, {"detail": "something_else"})

    assert sdk_cli._preflight(url) == (False, None)


def test_200_means_a_live_session(sdk_cli, stub_server):
    url = stub_server(200, {"tenant_id": "alice", "groups": [], "roles": []})

    assert sdk_cli._preflight(url) == (False, None)


@pytest.mark.parametrize(
    "status,body",
    [
        (401, b"not json at all"),
        (401, b'["a", "list"]'),
        (503, b"<html>gateway</html>"),
        (500, b'{"detail": "boom"}'),
    ],
    ids=["non-json-401", "json-non-mapping", "non-json-503", "500"],
)
def test_malformed_and_unexpected_responses_are_quiet(
    sdk_cli, stub_server, status, body
):
    url = stub_server(status, body)

    assert sdk_cli._preflight(url) == (False, None)


@pytest.mark.parametrize(
    "login_info", [None, "", 42, ["a"], {"a": "b"}], ids=str
)
def test_a_non_string_login_info_is_dropped(sdk_cli, stub_server, login_info):
    url = stub_server(401, {"detail": "missing_authorization", "login_info": login_info})

    assert sdk_cli._preflight(url) == (False, None)


def test_connection_refused_is_quiet(sdk_cli, capsys):
    """Port 1 on loopback: nothing listens, so this is a refused connection."""
    assert sdk_cli._preflight("http://127.0.0.1:1") == (False, None)
    assert capsys.readouterr().err == ""


def test_a_trailing_slash_on_the_base_url_is_handled(sdk_cli, stub_server):
    url = stub_server(401, {"detail": "missing_authorization", "login_info": MESSAGE})

    assert sdk_cli._preflight(url + "/") == (False, MESSAGE)


# --------------------------------------------------------------------------- #
# _do_login: where and how often the message is printed
# --------------------------------------------------------------------------- #

@pytest.fixture
def login_harness(sdk_cli, monkeypatch):
    """Drive ``_do_login`` with canned prompts and no registered backend."""

    def run(preflight_result, username="", password=""):
        monkeypatch.setattr(sdk_cli, "_registered_base", lambda _name: None)
        monkeypatch.setattr(sdk_cli, "_preflight", lambda _url: preflight_result)
        monkeypatch.setattr("builtins.input", lambda _prompt="": username)
        monkeypatch.setattr(sdk_cli.getpass, "getpass", lambda _prompt="": password)
        return sdk_cli._do_login("sbs", "http://example.invalid")

    return run


def test_the_message_precedes_the_prompt_on_stderr(login_harness, capsys):
    """Empty credentials short-circuit locally — after the banner has printed."""
    assert login_harness((False, MESSAGE)) == 2

    captured = capsys.readouterr()
    assert MESSAGE in captured.err
    assert captured.out == "", "stdout stays clean for the `Signed in as ...` line"
    # Printed before the local credential check, i.e. before any attempt.
    assert captured.err.index(MESSAGE) < captured.err.index(
        "Username and password are required"
    )


def test_the_message_is_printed_once_across_a_full_failed_login(
    sdk_cli, monkeypatch, capsys
):
    """A whole run, right through a rejected credential — still one banner.

    This is the property that makes the CLI match the UI: the message is a
    pre-attempt banner, never a post-failure one.
    """
    import subprocess

    monkeypatch.setattr(sdk_cli, "_registered_base", lambda _name: None)
    monkeypatch.setattr(sdk_cli, "_preflight", lambda _url: (False, MESSAGE))
    monkeypatch.setattr(sdk_cli, "_ensure_connected", lambda *a, **k: None)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "alice")
    monkeypatch.setattr(sdk_cli.getpass, "getpass", lambda _prompt="": "wrong")
    monkeypatch.setattr(
        sdk_cli.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(
            args=a[0] if a else [],
            returncode=1,
            stdout="",
            stderr="401 Unauthorized: invalid_credentials",
        ),
    )

    assert sdk_cli._do_login("sbs", "http://example.invalid") == 1

    captured = capsys.readouterr()
    assert captured.err.count(MESSAGE) == 1
    assert "Login failed: invalid_credentials" in captured.err
    # The banner came first; the failure is reported after.
    assert captured.err.index(MESSAGE) < captured.err.index("Login failed")


def test_nothing_is_printed_when_there_is_no_message(login_harness, capsys):
    assert login_harness((False, None)) == 2

    assert capsys.readouterr().err.strip() == "Username and password are required"


def test_auth_disabled_short_circuits_before_any_prompt(login_harness, capsys):
    """The pre-existing exit-2 path, unchanged."""
    assert login_harness((True, None)) == 2

    captured = capsys.readouterr()
    assert "no login required" in captured.err
    assert "Username and password are required" not in captured.err


# --------------------------------------------------------------------------- #
# The CLI/REST seam
# --------------------------------------------------------------------------- #

def test_preflight_reads_the_real_servers_401_body(sdk_cli, stub_server, tmp_path):
    """End-to-end contract: the bytes the server sends are the bytes we parse.

    The 401 body is produced by the real ``/auth/whoami`` handler against a
    real ``access_control_config.yaml``, then replayed over a socket — which is
    what ``_preflight`` needs, since it speaks urllib rather than ASGI. A change
    to either side of the contract (the key name, the status, the shape) fails
    here.

    Only the auth API is registered, not a whole ``SBS()``: building one would
    reset the process-wide service registry that the session-scoped e2e server
    fixture owns.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from skillberry_store.access_control.config import load_config
    from skillberry_store.access_control.sessions import SessionStore
    from skillberry_store.fast_api.auth_api import register_auth_api

    cfg_path = tmp_path / "acl.yaml"
    cfg_path.write_text(
        "mode: standalone\n"
        "standalone:\n"
        "  users: []\n"
        f'  login_info:\n    enabled: true\n    message: "{MESSAGE}"\n'
    )
    cfg = load_config(str(cfg_path))
    assert cfg.login_info == MESSAGE

    app = FastAPI()
    register_auth_api(app, cfg=cfg, sessions=SessionStore())
    response = TestClient(app).get("/auth/whoami")

    assert response.status_code == 401
    url = stub_server(401, response.content)

    assert sdk_cli._preflight(url) == (False, MESSAGE)

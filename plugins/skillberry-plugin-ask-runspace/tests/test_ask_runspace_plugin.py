import os
from unittest.mock import Mock, patch

from skillberry_plugin_ask_runspace.presets import PRESETS
from skillberry_plugin_ask_runspace.plugin import SkillberryPluginAskRunspace


def test_presets_have_id_label_prompt_skills():
    assert PRESETS
    for p in PRESETS:
        assert {"id", "label", "prompt", "skills"} <= set(p)
        assert isinstance(p["skills"], list)


def test_preset_skills_prefilled():
    by_id = {p["id"]: p for p in PRESETS}
    assert any("evo-graph" in s for s in by_id["optimize"]["skills"])
    assert any("skill-creator" in s for s in by_id["skill"]["skills"])


def test_generic_custom_preset_is_empty():
    by_id = {p["id"]: p for p in PRESETS}
    assert by_id["custom"]["prompt"] == ""
    assert by_id["custom"]["skills"] == []


def _plugin(env):
    with patch.dict(os.environ, env, clear=True):
        with patch("skillberry_plugin_ask_runspace.plugin.runspace_agent", new=Mock()):
            with patch.object(SkillberryPluginAskRunspace, "_load_claude_settings", lambda self: None):
                return SkillberryPluginAskRunspace()


def test_disabled_without_credentials():
    p = _plugin({})
    assert p.is_enabled() is False
    assert "credentials" in p.get_status_message().lower()


def test_enabled_with_api_key():
    p = _plugin({"ANTHROPIC_API_KEY": "k"})
    assert p.is_enabled() is True


import asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _client(plugin):
    app = FastAPI()
    app.include_router(plugin.get_router(), prefix="/plugins/ask-runspace")
    return TestClient(app)


def test_presets_endpoint():
    p = _plugin({"ANTHROPIC_API_KEY": "k"})
    r = _client(p).get("/plugins/ask-runspace/presets")
    assert r.status_code == 200
    assert any(item["id"] == "tool" for item in r.json())


def test_run_then_status_ready(monkeypatch):
    p = _plugin({"ANTHROPIC_API_KEY": "k"})
    seen = {}

    async def fake_run(prompt, editable_dir, context_dir, options, mode, remote_skills=None, skills_dir=None):
        seen["remote_skills"] = remote_skills
        class R: session_id = "sess123"
        return R()

    monkeypatch.setattr("skillberry_plugin_ask_runspace.runner.run_task_session", fake_run)
    monkeypatch.setattr("skillberry_plugin_ask_runspace.runner.read_summary",
                        lambda session_id, editable_dir, mode: "# Done")

    client = _client(p)
    resp = client.post("/plugins/ask-runspace/run",
                       json={"request": "do x", "skills": ["https://x/y"], "execution_mode": "local"})
    assert resp.status_code == 200
    job_id = resp.json()["data"]["job_id"]

    # Drain the background task, then poll status.
    for _ in range(50):
        s = client.get(f"/plugins/ask-runspace/status/{job_id}").json()
        if s["status"] != "pending":
            break
    assert s["status"] == "ready"
    assert s["summary_md"] == "# Done"
    assert s["session_id"] == "sess123"
    assert seen["remote_skills"] == ["https://x/y"]
    assert "Loaded skills" in s["message"]


def test_run_cleans_up_temp_dir(monkeypatch):
    p = _plugin({"ANTHROPIC_API_KEY": "k"})
    seen = {}

    async def fake_run(prompt, editable_dir, context_dir, options, mode, remote_skills=None, skills_dir=None):
        seen["editable_dir"] = editable_dir  # inside the scratch temp dir
        class R: session_id = "sess123"
        return R()

    monkeypatch.setattr("skillberry_plugin_ask_runspace.runner.run_task_session", fake_run)
    monkeypatch.setattr("skillberry_plugin_ask_runspace.runner.read_summary",
                        lambda session_id, editable_dir, mode: "# Done")

    client = _client(p)
    job_id = client.post("/plugins/ask-runspace/run", json={"request": "do x"}).json()["data"]["job_id"]
    for _ in range(50):
        s = client.get(f"/plugins/ask-runspace/status/{job_id}").json()
        if s["status"] != "pending":
            break
    assert s["status"] == "ready"
    # The scratch workspace (parent of editable/) must be removed after the run.
    assert not os.path.exists(os.path.dirname(seen["editable_dir"]))


def test_status_ready_shows_message_when_no_summary(monkeypatch):
    p = _plugin({"ANTHROPIC_API_KEY": "k"})

    async def fake_run(prompt, editable_dir, context_dir, options, mode, remote_skills=None, skills_dir=None):
        class R: session_id = "sess123"
        return R()

    monkeypatch.setattr("skillberry_plugin_ask_runspace.runner.run_task_session", fake_run)
    monkeypatch.setattr("skillberry_plugin_ask_runspace.runner.read_summary",
                        lambda session_id, editable_dir, mode: None)

    client = _client(p)
    job_id = client.post("/plugins/ask-runspace/run", json={"request": "do x"}).json()["data"]["job_id"]
    for _ in range(50):
        s = client.get(f"/plugins/ask-runspace/status/{job_id}").json()
        if s["status"] != "pending":
            break
    assert s["status"] == "ready"
    assert s["summary_md"]  # non-empty fallback message, not None
    assert "summary" in s["summary_md"].lower()


def test_keep_workspace_retains_dir_and_cleanup_endpoint_deletes_it(monkeypatch):
    p = _plugin({"ANTHROPIC_API_KEY": "k"})

    async def fake_run(prompt, editable_dir, context_dir, options, mode, remote_skills=None, skills_dir=None):
        class R: session_id = "sess123"
        return R()

    monkeypatch.setattr("skillberry_plugin_ask_runspace.runner.run_task_session", fake_run)
    monkeypatch.setattr("skillberry_plugin_ask_runspace.runner.read_summary",
                        lambda session_id, editable_dir, mode: "# Done")

    client = _client(p)
    job_id = client.post("/plugins/ask-runspace/run",
                         json={"request": "do x", "keep_workspace": True}).json()["data"]["job_id"]
    for _ in range(50):
        s = client.get(f"/plugins/ask-runspace/status/{job_id}").json()
        if s["status"] != "pending":
            break
    assert s["status"] == "ready"
    ws = s["workspace_dir"]
    assert os.path.isdir(ws)  # kept, not deleted

    # The cleanup endpoint deletes it; a second call 404s.
    assert client.post(f"/plugins/ask-runspace/cleanup/{job_id}").status_code == 200
    assert not os.path.exists(ws)
    assert client.post(f"/plugins/ask-runspace/cleanup/{job_id}").status_code == 404


def test_ui_config_shape():
    p = _plugin({"ANTHROPIC_API_KEY": "k"})
    cfg = p.get_ui_config()
    action = cfg["actions"][0]
    props = action["params_schema"]["properties"]
    assert props["request"]["format"] == "textarea"
    assert action["params_schema"]["required"] == ["request"]
    assert props["preset_id"]["x-options-from"].endswith("/presets")
    assert props["preset_id"]["x-prefill"] == {"request": "prompt", "skills": "skills"}
    assert props["skills"]["type"] == "array"
    assert props["skills_upload_id"]["format"] == "directory-upload"
    assert props["skills_upload_id"]["x-upload-endpoint"].endswith("/upload-skills")
    assert props["mcp_servers"]["format"] == "textarea"
    assert props["keep_workspace"]["type"] == "boolean"
    assert props["keep_workspace"].get("default") is True
    # Hidden in server mode (the server keeps its own session workspace).
    assert props["keep_workspace"]["x-visible-when"] == {"field": "use_runspace_server", "equals": False}
    assert action["async_action"]["timeout_ms"] >= 600_000
    assert props["use_runspace_server"]["type"] == "boolean"
    assert props["use_runspace_server"].get("default") is False
    assert props["runspace_server_url"]["x-visible-when"] == {"field": "use_runspace_server", "equals": True}
    assert action["async_action"]["cleanup_action"]["when_field"] == "workspace_dir"
    assert action["async_action"]["result_markdown_field"] == "summary_md"
    assert action["async_action"]["result_link"]["field"] == "session_url"
    # mcp_servers is prefilled with the store's own MCP so the agent can use it.
    import json as _json
    default_mcp = _json.loads(props["mcp_servers"]["default"])
    store = default_mcp["skillberry-store"]
    assert store["type"] == "sse"
    assert store["url"].endswith("/control_sse")


def test_store_mcp_url_uses_sbs_port_and_localhost():
    from skillberry_plugin_ask_runspace.plugin import _store_mcp_url

    with patch.dict(os.environ, {"SBS_HOST": "0.0.0.0", "SBS_PORT": "8123"}, clear=False):
        assert _store_mcp_url() == "http://localhost:8123/control_sse"


def test_store_server_name_matches_control_sse():
    from skillberry_plugin_ask_runspace.plugin import _store_server_name

    assert _store_server_name(None) is None
    assert _store_server_name({"fetch": {"command": "npx"}}) is None
    assert _store_server_name(
        {"skillberry-store": {"type": "sse", "url": "http://localhost:8000/control_sse"}}
    ) == "skillberry-store"
    # Trailing slash is tolerated.
    assert _store_server_name(
        {"store": {"type": "sse", "url": "http://h:8000/control_sse/"}}
    ) == "store"


def test_prompt_gets_store_guidance_when_store_mcp_present(monkeypatch):
    p = _plugin({"ANTHROPIC_API_KEY": "k"})
    seen = {}

    async def fake_run(prompt, editable_dir, context_dir, options, mode, remote_skills=None, skills_dir=None):
        seen["prompt"] = prompt
        class R: session_id = "s"
        return R()

    monkeypatch.setattr("skillberry_plugin_ask_runspace.runner.run_task_session", fake_run)
    monkeypatch.setattr("skillberry_plugin_ask_runspace.runner.read_summary",
                        lambda *a, **k: "# done")

    client = _client(p)
    job_id = client.post(
        "/plugins/ask-runspace/run",
        json={
            "request": "make a mul tool",
            "mcp_servers": '{"skillberry-store": {"type": "sse", "url": "http://localhost:8000/control_sse"}}',
        },
    ).json()["data"]["job_id"]
    for _ in range(50):
        s = client.get(f"/plugins/ask-runspace/status/{job_id}").json()
        if s["status"] != "pending":
            break
    assert s["status"] == "ready"
    assert seen["prompt"].startswith("make a mul tool")
    assert "Skillberry Store MCP server" in seen["prompt"]
    assert "mcp__skillberry-store__" in seen["prompt"]


def test_prompt_unchanged_without_store_mcp(monkeypatch):
    p = _plugin({"ANTHROPIC_API_KEY": "k"})
    seen = {}

    async def fake_run(prompt, editable_dir, context_dir, options, mode, remote_skills=None, skills_dir=None):
        seen["prompt"] = prompt
        class R: session_id = "s"
        return R()

    monkeypatch.setattr("skillberry_plugin_ask_runspace.runner.run_task_session", fake_run)
    monkeypatch.setattr("skillberry_plugin_ask_runspace.runner.read_summary",
                        lambda *a, **k: "# done")

    client = _client(p)
    # A non-store MCP only → no store guidance appended.
    job_id = client.post(
        "/plugins/ask-runspace/run",
        json={"request": "do x", "mcp_servers": '{"fetch": {"command": "npx"}}'},
    ).json()["data"]["job_id"]
    for _ in range(50):
        s = client.get(f"/plugins/ask-runspace/status/{job_id}").json()
        if s["status"] != "pending":
            break
    assert s["status"] == "ready"
    assert seen["prompt"] == "do x"


def test_normalize_server_url():
    from skillberry_plugin_ask_runspace.runner import normalize_server_url

    assert normalize_server_url(None) == "http://localhost:6767"
    assert normalize_server_url("") == "http://localhost:6767"
    assert normalize_server_url("localhost:6767/") == "http://localhost:6767"
    assert normalize_server_url("https://host:9000/") == "https://host:9000"


def test_run_uses_server_when_enabled(monkeypatch):
    p = _plugin({"ANTHROPIC_API_KEY": "k"})
    seen = {}

    async def fake_server(base_url, prompt, editable_dir, context_dir, mode,
                          remote_skills=None, skills_dir=None, mcp_servers=None,
                          agent_env=None, on_started=None):
        from skillberry_plugin_ask_runspace.runner import ServerRunResult
        seen.update(base_url=base_url, prompt=prompt, mode=mode, mcp_servers=mcp_servers)
        return ServerRunResult(
            session_id="srv-1", summary="# Server done",
            session_url="http://localhost:6767/ui/sessions/srv-1",
        )

    # The library path must NOT be used when the server is enabled.
    async def boom(*a, **k):
        raise AssertionError("library run_task_session should not be called in server mode")

    monkeypatch.setattr("skillberry_plugin_ask_runspace.runner.run_via_server", fake_server)
    monkeypatch.setattr("skillberry_plugin_ask_runspace.runner.run_task_session", boom)

    client = _client(p)
    job_id = client.post(
        "/plugins/ask-runspace/run",
        json={
            "request": "do x",
            "use_runspace_server": True,
            "runspace_server_url": "http://localhost:6767",
            "mcp_servers": '{"fetch": {"command": "npx"}}',
        },
    ).json()["data"]["job_id"]
    for _ in range(50):
        s = client.get(f"/plugins/ask-runspace/status/{job_id}").json()
        if s["status"] != "pending":
            break
    assert s["status"] == "ready"
    assert s["summary_md"] == "# Server done"
    assert s["session_url"] == "http://localhost:6767/ui/sessions/srv-1"
    assert seen["base_url"] == "http://localhost:6767"
    assert seen["mcp_servers"] == {"fetch": {"command": "npx"}}


def test_status_pending_surfaces_job_meta_session_url():
    # A pending job exposes mid-run info (e.g. the server session URL recorded by
    # run_via_server's on_started callback) so the UI can link to it before the
    # run completes.
    p = _plugin({"ANTHROPIC_API_KEY": "k"})
    client = _client(p)

    class _NotDone:
        def done(self):
            return False

    p._jobs["job-x"] = _NotDone()
    p._job_meta["job-x"] = {"session_url": "http://localhost:6767/ui/sessions/srv-1"}

    s = client.get("/plugins/ask-runspace/status/job-x").json()
    assert s["status"] == "pending"
    assert s["session_url"].endswith("/ui/sessions/srv-1")


def test_run_via_server_invokes_on_started_then_returns_summary(monkeypatch):
    # Unit-test run_via_server end-to-end against a mocked runspace server: it
    # reports the session URL via on_started before polling, then returns the
    # summary once the session completes.
    import httpx
    from skillberry_plugin_ask_runspace import runner

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/run":
            return httpx.Response(200, json={"session_id": "srv-9", "status": "pending"})
        if path == "/sessions/srv-9":
            return httpx.Response(200, json={"status": "completed", "has_summary": True})
        if path == "/sessions/srv-9/summary":
            return httpx.Response(200, json={"content": "# Done"})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient

    def patched_client(*a, **k):
        k["transport"] = transport
        return real_client(*a, **k)

    monkeypatch.setattr(httpx, "AsyncClient", patched_client)

    started = {}
    result = asyncio.run(runner.run_via_server(
        "localhost:6767", "do x", "/e", "/c", "local",
        on_started=lambda sid, url: started.update(sid=sid, url=url),
        poll_interval=0.0,
    ))
    assert started["url"] == "http://localhost:6767/ui/sessions/srv-9"
    assert result.session_id == "srv-9"
    assert result.summary == "# Done"
    assert result.session_url == "http://localhost:6767/ui/sessions/srv-9"


def test_parse_mcp_servers_handles_json_wrapper_and_invalid():
    from skillberry_plugin_ask_runspace.plugin import _parse_mcp_servers

    bare = '{"fetch": {"command": "npx", "args": ["-y", "mcp-fetch"]}}'
    assert _parse_mcp_servers(bare) == {"fetch": {"command": "npx", "args": ["-y", "mcp-fetch"]}}
    # A full .mcp.json wrapper is unwrapped to the bare name→config map.
    wrapped = '{"mcpServers": {"fetch": {"command": "npx"}}}'
    assert _parse_mcp_servers(wrapped) == {"fetch": {"command": "npx"}}
    # Already-decoded dicts pass through; empty/None collapse to None.
    assert _parse_mcp_servers({"a": {}}) == {"a": {}}
    assert _parse_mcp_servers("") is None
    assert _parse_mcp_servers(None) is None
    import pytest
    with pytest.raises(ValueError):
        _parse_mcp_servers("{not json}")
    with pytest.raises(ValueError):
        _parse_mcp_servers("[1, 2]")


def test_run_rejects_invalid_mcp_servers():
    p = _plugin({"ANTHROPIC_API_KEY": "k"})
    r = _client(p).post("/plugins/ask-runspace/run",
                        json={"request": "do x", "mcp_servers": "{bad json"})
    assert r.status_code == 400


def test_run_forwards_skills_dir_and_mcp_servers(monkeypatch):
    p = _plugin({"ANTHROPIC_API_KEY": "k"})
    seen = {}

    async def fake_run(prompt, editable_dir, context_dir, options, mode, remote_skills=None, skills_dir=None):
        seen["skills_dir"] = skills_dir
        seen["mcp_servers"] = getattr(options, "mcp_servers", None)
        class R: session_id = "sess123"
        return R()

    monkeypatch.setattr("skillberry_plugin_ask_runspace.runner.run_task_session", fake_run)
    monkeypatch.setattr("skillberry_plugin_ask_runspace.runner.read_summary",
                        lambda session_id, editable_dir, mode: "# Done")

    client = _client(p)
    job_id = client.post(
        "/plugins/ask-runspace/run",
        json={
            "request": "do x",
            "skills_dir": "/srv/skills",
            "mcp_servers": '{"mcpServers": {"fetch": {"command": "npx"}}}',
        },
    ).json()["data"]["job_id"]
    for _ in range(50):
        s = client.get(f"/plugins/ask-runspace/status/{job_id}").json()
        if s["status"] != "pending":
            break
    assert s["status"] == "ready"
    assert seen["skills_dir"] == "/srv/skills"
    assert seen["mcp_servers"] == {"fetch": {"command": "npx"}}


def test_materialize_skill_upload_strips_top_and_blocks_traversal():
    import tempfile
    from skillberry_plugin_ask_runspace.plugin import _safe_rel_parts, _materialize_skill_upload

    assert _safe_rel_parts("../etc/passwd") is None
    assert _safe_rel_parts("/abs/path") is None
    assert _safe_rel_parts("a/b/c.md") == ["a", "b", "c.md"]

    base = tempfile.mkdtemp()
    n = _materialize_skill_upload(base, [
        ("pack/skill-a/SKILL.md", b"a"),
        ("pack/skill-a/tool.py", b"x"),
        ("../evil", b"nope"),
    ])
    assert n == 2  # the traversal entry is skipped
    # The single common top folder ("pack") is stripped → skills sit at the root.
    assert os.path.isfile(os.path.join(base, "skill-a", "SKILL.md"))
    assert not os.path.exists(os.path.join(base, "evil"))


def test_upload_skills_then_run_consumes_and_cleans_up(monkeypatch):
    p = _plugin({"ANTHROPIC_API_KEY": "k"})
    client = _client(p)

    up = client.post(
        "/plugins/ask-runspace/upload-skills",
        files=[
            ("files", ("my-skills/skill-a/SKILL.md", b"# A", "text/markdown")),
            ("files", ("my-skills/skill-b/SKILL.md", b"# B", "text/markdown")),
        ],
    )
    assert up.status_code == 200
    assert up.json()["data"]["file_count"] == 2
    upload_id = up.json()["data"]["upload_id"]

    seen = {}

    async def fake_run(prompt, editable_dir, context_dir, options, mode, remote_skills=None, skills_dir=None):
        seen["skills_dir"] = skills_dir
        seen["has_skill_a"] = os.path.isfile(os.path.join(skills_dir, "skill-a", "SKILL.md"))
        class R: session_id = "s"
        return R()

    monkeypatch.setattr("skillberry_plugin_ask_runspace.runner.run_task_session", fake_run)
    monkeypatch.setattr("skillberry_plugin_ask_runspace.runner.read_summary",
                        lambda session_id, editable_dir, mode: "# Done")

    job_id = client.post("/plugins/ask-runspace/run",
                         json={"request": "do x", "skills_upload_id": upload_id}).json()["data"]["job_id"]
    for _ in range(50):
        s = client.get(f"/plugins/ask-runspace/status/{job_id}").json()
        if s["status"] != "pending":
            break
    assert s["status"] == "ready"
    assert seen["has_skill_a"] is True
    # The uploaded temp dir is removed once the run consumes it.
    assert not os.path.exists(seen["skills_dir"])

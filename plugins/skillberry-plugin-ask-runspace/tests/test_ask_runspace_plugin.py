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
    assert any("mcp-builder" in s for s in by_id["mcp"]["skills"])


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
    assert props["skills_dir"]["type"] == "string"
    assert props["mcp_servers"]["format"] == "textarea"
    assert props["keep_workspace"]["type"] == "boolean"
    assert props["keep_workspace"].get("default") is False
    assert action["async_action"]["cleanup_action"]["when_field"] == "workspace_dir"
    assert action["async_action"]["result_markdown_field"] == "summary_md"


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

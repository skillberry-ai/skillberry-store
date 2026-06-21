import os
from unittest.mock import Mock, patch

from skillberry_plugin_ask_runspace.presets import PRESETS, compose_prompt
from skillberry_plugin_ask_runspace.plugin import SkillberryPluginAskRunspace


def test_presets_have_id_label_guidance():
    assert PRESETS
    for p in PRESETS:
        assert {"id", "label", "guidance"} <= set(p)


def test_compose_prompt_combines_guidance_and_request():
    pid = PRESETS[0]["id"]
    out = compose_prompt(pid, "do the thing")
    assert "do the thing" in out
    assert PRESETS[0]["guidance"] in out


def test_compose_prompt_request_only():
    assert compose_prompt(None, "just this") .strip().endswith("just this")


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

    async def fake_run(prompt, editable_dir, context_dir, options, mode):
        class R: session_id = "sess123"
        return R()

    monkeypatch.setattr("skillberry_plugin_ask_runspace.runner.run_task_session", fake_run)
    monkeypatch.setattr("skillberry_plugin_ask_runspace.runner.read_summary",
                        lambda session_id, editable_dir, mode: "# Done\nall good")

    client = _client(p)
    resp = client.post("/plugins/ask-runspace/run", json={"request": "do x", "execution_mode": "local"})
    assert resp.status_code == 200
    job_id = resp.json()["data"]["job_id"]

    # Drain the background task, then poll status.
    for _ in range(50):
        s = client.get(f"/plugins/ask-runspace/status/{job_id}").json()
        if s["status"] != "pending":
            break
    assert s["status"] == "ready"
    assert s["summary_md"] == "# Done\nall good"
    assert s["session_id"] == "sess123"

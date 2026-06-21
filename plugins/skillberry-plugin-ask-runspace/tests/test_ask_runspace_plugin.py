import os
from unittest.mock import Mock, patch

from skillberry_plugin_ask_runspace.presets import PRESETS, compose_prompt
from skillberry_plugin_ask_runspace.plugin import SkillberryPluginAskRunspace


def test_presets_have_id_label_guidance():
    assert PRESETS
    for p in PRESETS:
        assert {"id", "label", "guidance"} <= set(p)


def test_compose_prompt_combines_guidance_and_request():
    # Use a preset that actually has guidance (the first one is the generic
    # empty-guidance option).
    preset = next(p for p in PRESETS if p["guidance"].strip())
    out = compose_prompt(preset["id"], "do the thing")
    assert "do the thing" in out
    assert preset["guidance"] in out


def test_compose_prompt_request_only():
    assert compose_prompt(None, "just this").strip().endswith("just this")


def test_compose_prompt_generic_preset_is_request_only():
    # The generic "custom" preset has empty guidance -> request used verbatim.
    assert compose_prompt("custom", "just this") == "just this"


def test_optimize_preset_present():
    assert any(p["id"] == "optimize" for p in PRESETS)


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


def test_run_cleans_up_temp_dir(monkeypatch):
    p = _plugin({"ANTHROPIC_API_KEY": "k"})
    seen = {}

    async def fake_run(prompt, editable_dir, context_dir, options, mode):
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

    async def fake_run(prompt, editable_dir, context_dir, options, mode):
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

    async def fake_run(prompt, editable_dir, context_dir, options, mode):
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
    assert props["keep_workspace"]["type"] == "boolean"
    assert props["keep_workspace"].get("default") is False
    assert action["async_action"]["cleanup_action"]["when_field"] == "workspace_dir"
    assert action["async_action"]["result_markdown_field"] == "summary_md"

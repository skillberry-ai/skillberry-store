"""Tests for the Skill Optimizer plugin (SDK-based)."""

import json
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from skillberry_plugin_skill_optimizer.prompt import (
    REQUIRED_OUTPUTS_FILENAME,
    REQUIRED_OUTPUTS_TEMPLATE,
    build_runspace_prompt,
)


# ---------------------------------------------------------------------------
# prompt.py tests
# ---------------------------------------------------------------------------

def test_required_outputs_template_has_all_fields():
    required_keys = {
        "skill_name", "skill_description", "optimization_rationale",
        "issues_addressed", "tools_added", "tools_modified", "tools_removed",
        "snippets_added", "snippets_modified", "snippets_removed",
        "ready_for_deployment",
    }
    assert required_keys == set(REQUIRED_OUTPUTS_TEMPLATE.keys())


def test_required_outputs_filename():
    assert REQUIRED_OUTPUTS_FILENAME == "required_outputs.json"


def test_build_prompt_no_context():
    prompt = build_runspace_prompt(
        has_metadata=False, has_trajectories=False, has_additional_context=False
    )
    assert "optimizing a Skillberry skill" in prompt
    assert "REQUIRED OUTPUT CONTRACT" in prompt
    assert "required_outputs.json" in prompt
    assert "SKILLBERRY STORE ANTHROPIC SKILL FORMAT" in prompt
    assert "skill_metadata.json" not in prompt
    assert "trajectories/" not in prompt
    assert "additional_context/" not in prompt


def test_build_prompt_with_metadata():
    prompt = build_runspace_prompt(
        has_metadata=True, has_trajectories=False, has_additional_context=False
    )
    assert "skill_metadata.json" in prompt


def test_build_prompt_with_trajectories():
    prompt = build_runspace_prompt(
        has_metadata=False, has_trajectories=True, has_additional_context=False
    )
    assert "trajectories/" in prompt
    assert "reward" in prompt
    assert "overfit" in prompt


def test_build_prompt_with_additional_context():
    prompt = build_runspace_prompt(
        has_metadata=False, has_trajectories=False, has_additional_context=True
    )
    assert "additional_context/" in prompt


def test_build_prompt_all_context():
    prompt = build_runspace_prompt(
        has_metadata=True, has_trajectories=True, has_additional_context=True
    )
    assert "skill_metadata.json" in prompt
    assert "trajectories/" in prompt
    assert "additional_context/" in prompt


def test_build_prompt_contains_required_outputs_template():
    prompt = build_runspace_prompt(
        has_metadata=False, has_trajectories=False, has_additional_context=False
    )
    for key in REQUIRED_OUTPUTS_TEMPLATE:
        assert key in prompt


from skillberry_plugin_skill_optimizer.plugin import SkillberryPluginSkillOptimizer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_store():
    """Build an AsyncMock StoreClient with the surface the plugin uses."""
    store = AsyncMock()
    store.get_skill = AsyncMock(return_value={
        "uuid": "skill-uuid-123",
        "name": "my-skill",
        "description": "A test skill",
        "tags": ["python", "test"],
        "extra": {},
        "tool_uuids": ["tool-uuid-1"],
        "snippet_uuids": [],
        "tools": [
            {
                "uuid": "tool-uuid-1",
                "name": "my_tool",
                "description": "A tool",
                "programming_language": "python",
                "module_name": "my_tool.py",
                "tags": [],
            }
        ],
        "snippets": [],
    })
    store.list_skills = AsyncMock(return_value=[{"name": "other-skill"}])
    store.get = AsyncMock(return_value="def my_tool():\n    pass\n")
    store.post = AsyncMock(return_value={"uuid": "new-uuid", "name": "created"})
    store.patch_skill = AsyncMock(return_value={"uuid": "new-uuid"})
    return store


@pytest.fixture
def plugin():
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("skillberry_plugin_skill_optimizer.plugin.runspace_agent", new=Mock()):
            p = SkillberryPluginSkillOptimizer()
    return p


@pytest.fixture
def mock_store():
    return _make_store()


def _wire_store(plugin, store):
    """Attach a mock store and stub the create/update helpers used by optimize_skill."""
    plugin._store = store
    # Route _create_tool through the mock so tests don't need a live http server.
    plugin._create_tool = AsyncMock(return_value={"uuid": "new-tool-uuid", "name": "my_tool"})
    plugin._create_snippet = AsyncMock(return_value={"uuid": "new-snip-uuid", "name": "my_snip"})
    plugin._create_skill = AsyncMock(return_value={
        "uuid": "new-skill-uuid",
        "name": "my-skill_optimized",
        "description": "Optimized skill",
    })
    plugin._update_skill_metadata = AsyncMock(return_value=True)
    return plugin


# ---------------------------------------------------------------------------
# Manifest / init tests
# ---------------------------------------------------------------------------

def test_plugin_manifest_slug(plugin):
    assert plugin.manifest.slug == "skill-optimizer"


def test_plugin_manifest_type(plugin):
    assert plugin.manifest.plugin_type == "optimizer"


def test_plugin_manifest_version(plugin):
    assert plugin.manifest.version == "0.1.0"


def test_plugin_manifest_has_api(plugin):
    assert plugin.manifest.has_api is True


def test_is_enabled_with_runspace_and_credentials(plugin):
    assert plugin.is_enabled() is True


def test_is_enabled_without_runspace():
    with patch("skillberry_plugin_skill_optimizer.plugin.runspace_agent", new=None):
        p = SkillberryPluginSkillOptimizer()
    assert p.is_enabled() is False


def test_is_enabled_without_credentials():
    env = {k: v for k, v in os.environ.items()
           if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN")}
    with patch.dict(os.environ, env, clear=True):
        with patch("skillberry_plugin_skill_optimizer.plugin.runspace_agent", new=Mock()):
            with patch.object(SkillberryPluginSkillOptimizer, "_load_claude_settings", lambda self: None):
                p = SkillberryPluginSkillOptimizer()
    assert p.is_enabled() is False


def test_status_message_ready(plugin):
    msg = plugin.get_status_message()
    assert "Ready" in msg


def test_status_message_missing_runspace():
    with patch("skillberry_plugin_skill_optimizer.plugin.runspace_agent", new=None):
        p = SkillberryPluginSkillOptimizer()
    assert "runspace-agent" in p.get_status_message()


def test_status_message_missing_credentials():
    env = {k: v for k, v in os.environ.items()
           if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN")}
    with patch.dict(os.environ, env, clear=True):
        with patch("skillberry_plugin_skill_optimizer.plugin.runspace_agent", new=Mock()):
            with patch.object(SkillberryPluginSkillOptimizer, "_load_claude_settings", lambda self: None):
                p = SkillberryPluginSkillOptimizer()
    assert "credentials" in p.get_status_message().lower()


# ---------------------------------------------------------------------------
# is_ready (SDK lifecycle)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_is_ready_reports_ready_when_enabled(plugin):
    ready = await plugin.is_ready()
    assert ready["ready"] is True
    assert ready["missing_config"] == []


@pytest.mark.asyncio
async def test_is_ready_reports_missing_runspace():
    with patch("skillberry_plugin_skill_optimizer.plugin.runspace_agent", new=None):
        p = SkillberryPluginSkillOptimizer()
    ready = await p.is_ready()
    assert ready["ready"] is False
    assert "runspace-agent" in ready["missing_config"]


# ---------------------------------------------------------------------------
# Naming tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_naming_no_conflict(plugin, mock_store):
    plugin._store = mock_store
    name = await plugin._generate_output_skill_name("my-skill")
    assert name == "my-skill_optimized"


@pytest.mark.asyncio
async def test_naming_conflict_appends_1(plugin, mock_store):
    mock_store.list_skills = AsyncMock(return_value=[
        {"name": "other-skill"},
        {"name": "my-skill_optimized"},
    ])
    plugin._store = mock_store
    name = await plugin._generate_output_skill_name("my-skill")
    assert name == "my-skill_optimized(1)"


@pytest.mark.asyncio
async def test_naming_conflict_appends_2(plugin, mock_store):
    mock_store.list_skills = AsyncMock(return_value=[
        {"name": "my-skill_optimized"},
        {"name": "my-skill_optimized(1)"},
    ])
    plugin._store = mock_store
    name = await plugin._generate_output_skill_name("my-skill")
    assert name == "my-skill_optimized(2)"


@pytest.mark.asyncio
async def test_naming_user_override(plugin, mock_store):
    plugin._store = mock_store
    name = await plugin._generate_output_skill_name("my-skill", override="custom-name")
    assert name == "custom-name"
    mock_store.list_skills.assert_not_awaited()


# ---------------------------------------------------------------------------
# optimize_skill tests
# ---------------------------------------------------------------------------

def _make_mock_result(session_id="abc123def456"):
    result = Mock()
    result.success = True
    result.session_id = session_id
    result.agent_result = Mock(total_tokens=1000, total_cost_usd=0.01, error=None)
    return result


def _make_mock_tool():
    tool = Mock()
    tool.name = "my_tool"
    tool.description = "A tool"
    tool.programming_language = "python"
    tool.params = {}
    tool.returns = {}
    tool.tags = []
    tool.module_content = "def my_tool():\n    pass\n"
    tool.source_file_name = "my_tool.py"
    return tool


@pytest.mark.asyncio
async def test_optimize_skill_happy_path(plugin, mock_store):
    _wire_store(plugin, mock_store)

    fake_req_outputs = {
        **REQUIRED_OUTPUTS_TEMPLATE,
        "skill_name": "my-skill-v2",
        "optimization_rationale": "Improved tool descriptions",
        "tools_modified": ["my_tool"],
    }

    async def fake_optimize_session(prompt, skill_dir, context_dir, options, mode, plugin_inst):
        Path(skill_dir / REQUIRED_OUTPUTS_FILENAME).write_text(
            json.dumps(fake_req_outputs)
        )
        return _make_mock_result()

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch(
            "skillberry_plugin_skill_optimizer.plugin.optimize_skill_session",
            side_effect=fake_optimize_session,
        ), patch(
            "skillberry_plugin_skill_optimizer.plugin.export_skill_to_directory"
        ), patch(
            "skillberry_plugin_skill_optimizer.plugin.import_from_anthropic_skill",
            return_value=("my-skill-v2", "Optimized skill", [_make_mock_tool()], [], []),
        ), patch(
            "skillberry_plugin_skill_optimizer.plugin.session_workspace",
            return_value=Path(tmpdir),
        ):
            result = await plugin.optimize_skill(
                skill_uuid="skill-uuid-123",
                execution_mode="local",
            )

    assert result["success"] is True
    assert result["skill"]["name"] == "my-skill_optimized"
    assert result["tools_count"] == 1
    assert result["snippets_count"] == 0
    plugin._update_skill_metadata.assert_awaited_once()
    call_args = plugin._update_skill_metadata.call_args
    opt_meta = call_args[0][1]["optimization"]
    assert opt_meta["optimization_rationale"] == "Improved tool descriptions"
    assert opt_meta["source_skill_uuid"] == "skill-uuid-123"
    assert opt_meta["source_skill_name"] == "my-skill"


@pytest.mark.asyncio
async def test_skill_not_found_raises(plugin, mock_store):
    mock_store.get_skill = AsyncMock(return_value=None)
    _wire_store(plugin, mock_store)
    with pytest.raises(ValueError, match="not found"):
        await plugin.optimize_skill(skill_uuid="nonexistent-uuid")


@pytest.mark.asyncio
async def test_bad_trajectories_dir_raises(plugin, mock_store):
    _wire_store(plugin, mock_store)
    with pytest.raises(ValueError, match="trajectories_dir"):
        await plugin.optimize_skill(
            skill_uuid="skill-uuid-123",
            trajectories_dir="/nonexistent/path/to/trajectories",
        )


@pytest.mark.asyncio
async def test_bad_additional_context_dir_raises(plugin, mock_store):
    _wire_store(plugin, mock_store)
    with pytest.raises(ValueError, match="additional_context_dir"):
        await plugin.optimize_skill(
            skill_uuid="skill-uuid-123",
            additional_context_dir="/nonexistent/path/to/context",
        )


@pytest.mark.asyncio
async def test_missing_required_outputs_still_imports(plugin, mock_store):
    _wire_store(plugin, mock_store)

    async def fake_session_no_outputs(prompt, skill_dir, context_dir, options, mode, plugin_inst):
        return _make_mock_result()

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch(
            "skillberry_plugin_skill_optimizer.plugin.optimize_skill_session",
            side_effect=fake_session_no_outputs,
        ), patch(
            "skillberry_plugin_skill_optimizer.plugin.export_skill_to_directory"
        ), patch(
            "skillberry_plugin_skill_optimizer.plugin.import_from_anthropic_skill",
            return_value=("my-skill-v2", "Optimized", [_make_mock_tool()], [], []),
        ), patch(
            "skillberry_plugin_skill_optimizer.plugin.session_workspace",
            return_value=Path(tmpdir),
        ):
            result = await plugin.optimize_skill(
                skill_uuid="skill-uuid-123",
                execution_mode="local",
            )

    assert result["success"] is True
    plugin._update_skill_metadata.assert_awaited_once()


@pytest.mark.asyncio
async def test_metadata_context_written_when_enabled(plugin, mock_store):
    _wire_store(plugin, mock_store)
    written_context_files = []

    async def fake_session_capture(prompt, skill_dir, context_dir, options, mode, plugin_inst):
        if context_dir.exists():
            written_context_files.extend(
                str(p) for p in Path(context_dir).rglob("*") if p.is_file()
            )
        return _make_mock_result()

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch(
            "skillberry_plugin_skill_optimizer.plugin.optimize_skill_session",
            side_effect=fake_session_capture,
        ), patch(
            "skillberry_plugin_skill_optimizer.plugin.export_skill_to_directory"
        ), patch(
            "skillberry_plugin_skill_optimizer.plugin.import_from_anthropic_skill",
            return_value=("my-skill", "desc", [], [], []),
        ), patch(
            "skillberry_plugin_skill_optimizer.plugin.session_workspace",
            return_value=Path(tmpdir),
        ):
            await plugin.optimize_skill(
                skill_uuid="skill-uuid-123",
                include_metadata=True,
                execution_mode="local",
            )

    assert any("skill_metadata.json" in f for f in written_context_files)


# ---------------------------------------------------------------------------
# Router tests
# ---------------------------------------------------------------------------

def test_router_is_not_none(plugin):
    router = plugin.get_router()
    assert router is not None


def test_router_has_optimize_skill_endpoint(plugin):
    from fastapi.routing import APIRoute
    router = plugin.get_router()
    paths = [r.path for r in router.routes if isinstance(r, APIRoute)]
    assert "/optimize-skill" in paths


def test_router_returns_503_when_disabled():
    with patch("skillberry_plugin_skill_optimizer.plugin.runspace_agent", new=None):
        p = SkillberryPluginSkillOptimizer()
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(p.get_router())
    client = TestClient(app)
    response = client.post("/optimize-skill", json={"skill_uuid": "some-uuid"})
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_router_optimize_skill_endpoint(plugin, mock_store):
    plugin._store = mock_store
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(plugin.get_router())
    client = TestClient(app)

    with patch.object(
        plugin,
        "optimize_skill",
        new=AsyncMock(return_value={
            "success": True,
            "skill": {"uuid": "new-uuid", "name": "my-skill_optimized"},
            "tools_count": 1,
            "snippets_count": 0,
            "optimization_rationale": "Improved",
        }),
    ):
        response = client.post("/optimize-skill", json={"skill_uuid": "skill-uuid-123"})

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["skill_name"] == "my-skill_optimized"
    assert data["skill_uuid"] == "new-uuid"


# ---------------------------------------------------------------------------
# UI config tests
# ---------------------------------------------------------------------------

def test_ui_config_not_none(plugin):
    assert plugin.get_ui_config() is not None


def test_ui_config_shape(plugin):
    config = plugin.get_ui_config()
    assert config["icon"] == "SparklesIcon"
    assert config["color"] == "#F59E0B"
    assert len(config["actions"]) == 1


def test_ui_config_action(plugin):
    action = plugin.get_ui_config()["actions"][0]
    assert action["label"] == "Optimize Skill"
    assert "optimize-skill" in action["endpoint"]
    assert action["method"] == "POST"


def test_ui_config_params_schema(plugin):
    schema = plugin.get_ui_config()["actions"][0]["params_schema"]
    assert schema["required"] == ["skill_uuid"]
    props = schema["properties"]
    assert "skill_uuid" in props
    assert "output_skill_name" in props
    assert "include_metadata" in props
    assert props["include_metadata"].get("default") is True
    assert "trajectories_dir" in props
    assert "additional_context_dir" in props
    assert "execution_mode" in props
    assert "container" in props["execution_mode"]["enum"]
    assert "local" in props["execution_mode"]["enum"]


def test_get_cli_commands_returns_none(plugin):
    assert plugin.get_cli_commands() is None


# ---------------------------------------------------------------------------
# Claude settings.json env handling
# ---------------------------------------------------------------------------

def _make_plugin_with_settings(settings):
    """Instantiate the plugin with a stubbed ~/.claude/settings.json payload."""
    with patch("skillberry_plugin_skill_optimizer.plugin.runspace_agent", new=Mock()):
        with patch.object(
            SkillberryPluginSkillOptimizer, "_load_claude_settings", lambda self: None
        ):
            p = SkillberryPluginSkillOptimizer()
    p._claude_settings = settings
    return p


def test_check_credentials_reads_settings_env_block():
    settings = {"env": {"ANTHROPIC_BASE_URL": "https://gw", "ANTHROPIC_AUTH_TOKEN": "tok"}}
    clean = {k: v for k, v in os.environ.items()
             if not (k.startswith("ANTHROPIC_") or k.startswith("CLAUDE_"))}
    with patch.dict(os.environ, clean, clear=True):
        p = _make_plugin_with_settings(settings)
        assert p._check_credentials() is True


def test_build_claude_env_forwards_entire_settings_env_block():
    settings = {
        "env": {
            "ANTHROPIC_BASE_URL": "https://gw",
            "ANTHROPIC_AUTH_TOKEN": "tok",
            "ANTHROPIC_MODEL": "claude-opus-4-8",
            "ANTHROPIC_SMALL_FAST_MODEL": "claude-sonnet-4-6",
            "CLAUDE_CODE_SUBAGENT_MODEL": "claude-opus-4-8",
        }
    }
    clean = {k: v for k, v in os.environ.items()
             if not (k.startswith("ANTHROPIC_") or k.startswith("CLAUDE_"))}
    with patch.dict(os.environ, clean, clear=True):
        p = _make_plugin_with_settings(settings)
        env = p._build_claude_env()
    for key, value in settings["env"].items():
        assert env[key] == value


def test_build_claude_env_process_env_overrides_settings():
    settings = {"env": {"ANTHROPIC_MODEL": "from-settings"}}
    with patch.dict(os.environ, {"ANTHROPIC_MODEL": "from-process"}, clear=False):
        p = _make_plugin_with_settings(settings)
        env = p._build_claude_env()
    assert env["ANTHROPIC_MODEL"] == "from-process"

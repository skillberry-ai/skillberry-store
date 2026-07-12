"""Unit tests for SkillberryPluginSkillsShImporter — no live HTTP calls."""

import os
import uuid
import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from skillberry_plugin_skillssh_importer.plugin import (
    SkillberryPluginSkillsShImporter,
    _installs_tag,
    _audit_tags,
    _overall_audit_tag,
    _files_from_detail,
    _jwt_exp,
    _cached_token_valid,
    _invalidate_cache,
    snippet_name_from,
)
import skillberry_plugin_skillssh_importer.plugin as _plugin_module
from skillberry_store.plugins.base import PluginType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(token: str = "test-token") -> tuple:
    """Build a TestClient with the plugin mounted and its store API mocked."""
    plugin = SkillberryPluginSkillsShImporter()
    mock_store = MagicMock()

    def _create_tool(data, module_content, module_filename):
        return {"uuid": str(uuid.uuid4()), "name": data["name"]}

    def _create_snippet(data):
        return {"uuid": str(uuid.uuid4()), "name": data.get("name", "snippet")}

    def _create_skill(data):
        return {"uuid": str(uuid.uuid4()), "name": data["name"]}

    mock_store.create_tool.side_effect = _create_tool
    mock_store.create_snippet.side_effect = _create_snippet
    mock_store.create_skill.side_effect = _create_skill
    plugin.set_store_api(mock_store)

    app = FastAPI()
    app.include_router(plugin.get_router(), prefix="/plugins/skillssh-importer")
    return TestClient(app), plugin, mock_store


# ---------------------------------------------------------------------------
# Pure-unit tests
# ---------------------------------------------------------------------------

class TestInstallsTag:
    def test_large(self):
        assert _installs_tag(50_000) == "installs:10k+"

    def test_thousands(self):
        assert _installs_tag(5_000) == "installs:1k+"

    def test_hundreds(self):
        assert _installs_tag(500) == "installs:100+"

    def test_tens(self):
        assert _installs_tag(42) == "installs:10+"

    def test_single(self):
        assert _installs_tag(3) == "installs:<10"

    def test_zero(self):
        assert _installs_tag(0) == "installs:<10"


class TestAuditTags:
    def test_empty(self):
        assert _audit_tags([]) == []

    def test_single_pass(self):
        tags = _audit_tags([{"slug": "socket", "status": "pass"}])
        assert tags == ["audit:socket:pass"]

    def test_multiple(self):
        audits = [
            {"slug": "socket", "status": "pass"},
            {"slug": "snyk", "status": "warn"},
        ]
        tags = _audit_tags(audits)
        assert "audit:socket:pass" in tags
        assert "audit:snyk:warn" in tags

    def test_falls_back_to_provider(self):
        tags = _audit_tags([{"provider": "Gen Agent Trust Hub", "status": "pass"}])
        assert "audit:gen-agent-trust-hub:pass" in tags


class TestOverallAuditTag:
    def test_empty(self):
        assert _overall_audit_tag([]) is None

    def test_all_pass(self):
        assert _overall_audit_tag([{"status": "pass"}, {"status": "pass"}]) == "audit:pass"

    def test_any_warn(self):
        assert _overall_audit_tag([{"status": "pass"}, {"status": "warn"}]) == "audit:warn"

    def test_any_fail(self):
        assert _overall_audit_tag([{"status": "pass"}, {"status": "fail"}]) == "audit:fail"

    def test_fail_wins_over_warn(self):
        assert _overall_audit_tag([{"status": "warn"}, {"status": "fail"}]) == "audit:fail"


class TestFilesFromDetail:
    def test_empty_files(self):
        assert _files_from_detail({"files": []}) == []

    def test_none_files(self):
        assert _files_from_detail({}) == []

    def test_extracts_name_from_path(self):
        detail = {"files": [{"path": "skills/test/SKILL.md", "contents": "---\nname: Test\n---\n"}]}
        files = _files_from_detail(detail)
        assert files[0]["name"] == "SKILL.md"
        assert files[0]["path"] == "skills/test/SKILL.md"
        assert "name: Test" in files[0]["content"]

    def test_bare_filename(self):
        detail = {"files": [{"path": "README.md", "contents": "hello"}]}
        files = _files_from_detail(detail)
        assert files[0]["name"] == "README.md"


class TestSnippetNameFrom:
    def test_uses_name_attr(self):
        obj = MagicMock()
        obj.name = "my-snippet"
        assert snippet_name_from(obj) == "my-snippet"

    def test_falls_back_to_title(self):
        obj = MagicMock(spec=[])
        obj.title = "The Title"
        assert snippet_name_from(obj) == "The Title"

    def test_default(self):
        obj = MagicMock(spec=[])
        assert snippet_name_from(obj) == "snippet"


# ---------------------------------------------------------------------------
# Metadata & lifecycle
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Token utility helpers
# ---------------------------------------------------------------------------

class TestJwtExp:
    def _make_jwt(self, exp: int) -> str:
        import base64, json as _json
        header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(
            _json.dumps({"exp": exp}).encode()
        ).rstrip(b"=").decode()
        return f"{header}.{payload}.fakesig"

    def test_extracts_exp(self):
        t = self._make_jwt(9999999999)
        assert _jwt_exp(t) == 9999999999.0

    def test_non_jwt_returns_none(self):
        assert _jwt_exp("not.a.jwt.at.all.extra") is None

    def test_no_exp_field_returns_none(self):
        import base64, json as _json
        payload = base64.urlsafe_b64encode(b'{"sub":"x"}').rstrip(b"=").decode()
        token = f"h.{payload}.sig"
        assert _jwt_exp(token) is None


class TestCacheInvalidation:
    def setup_method(self):
        _invalidate_cache()

    def test_empty_cache_returns_none(self):
        assert _cached_token_valid() is None

    def test_valid_cache_hit(self):
        import time
        _plugin_module._TOKEN_CACHE = ("tok", time.time() + 3600)
        assert _cached_token_valid() == "tok"

    def test_expired_cache_returns_none(self):
        import time
        _plugin_module._TOKEN_CACHE = ("tok", time.time() - 10)
        assert _cached_token_valid() is None

    def test_invalidate_clears_cache(self):
        import time
        _plugin_module._TOKEN_CACHE = ("tok", time.time() + 3600)
        _invalidate_cache()
        assert _cached_token_valid() is None

    def teardown_method(self):
        _invalidate_cache()


class TestAutoTokenAcquisition:
    """Tests for _resolve_token auto-refresh via Node/@vercel/oidc."""

    def setup_method(self):
        _invalidate_cache()

    def teardown_method(self):
        _invalidate_cache()

    def test_env_var_returned_when_fresh(self):
        from skillberry_plugin_skillssh_importer.plugin import _resolve_token
        with patch.dict(os.environ, {"SKILLS_SH_TOKEN": "env-tok"}):
            with patch(
                "skillberry_plugin_skillssh_importer.plugin._jwt_exp",
                return_value=None,  # no exp → never expired
            ):
                assert _resolve_token(None) == "env-tok"

    def test_override_returned_directly(self):
        from skillberry_plugin_skillssh_importer.plugin import _resolve_token
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SKILLS_SH_TOKEN", None)
            assert _resolve_token("my-override") == "my-override"

    def test_acquire_called_when_no_env_or_cache(self):
        from skillberry_plugin_skillssh_importer.plugin import _resolve_token
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SKILLS_SH_TOKEN", None)
            with patch(
                "skillberry_plugin_skillssh_importer.plugin._acquire_via_vercel_oidc",
                return_value="fresh-token",
            ) as mock_acquire:
                with patch(
                    "skillberry_plugin_skillssh_importer.plugin._jwt_exp",
                    return_value=None,
                ):
                    tok = _resolve_token(None)
        assert tok == "fresh-token"
        mock_acquire.assert_called_once()

    def test_acquired_token_cached(self):
        from skillberry_plugin_skillssh_importer.plugin import _resolve_token
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SKILLS_SH_TOKEN", None)
            with patch(
                "skillberry_plugin_skillssh_importer.plugin._acquire_via_vercel_oidc",
                return_value="cached-token",
            ) as mock_acquire:
                with patch(
                    "skillberry_plugin_skillssh_importer.plugin._jwt_exp",
                    return_value=None,
                ):
                    _resolve_token(None)
                    # Second call must NOT call acquire again
                    _resolve_token(None)
        assert mock_acquire.call_count == 1

    def test_acquire_returns_none_resolves_none(self):
        from skillberry_plugin_skillssh_importer.plugin import _resolve_token
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SKILLS_SH_TOKEN", None)
            with patch(
                "skillberry_plugin_skillssh_importer.plugin._acquire_via_vercel_oidc",
                return_value=None,
            ):
                assert _resolve_token(None) is None

    def test_expired_env_token_falls_through_to_acquire(self):
        import time
        from skillberry_plugin_skillssh_importer.plugin import _resolve_token
        expired_tok = "env-tok"
        with patch.dict(os.environ, {"SKILLS_SH_TOKEN": expired_tok}):
            # Make _jwt_exp return a past timestamp only for the env token
            def _fake_exp(t):
                if t == expired_tok:
                    return time.time() - 3600  # already expired
                return None  # acquired token: no expiry
            with patch(
                "skillberry_plugin_skillssh_importer.plugin._jwt_exp",
                side_effect=_fake_exp,
            ):
                with patch(
                    "skillberry_plugin_skillssh_importer.plugin._acquire_via_vercel_oidc",
                    return_value="fresh-token",
                ) as mock_acquire:
                    tok = _resolve_token(None)
        assert tok == "fresh-token"
        mock_acquire.assert_called_once()


# ---------------------------------------------------------------------------
# Metadata & lifecycle
# ---------------------------------------------------------------------------

class TestPluginMetadata:
    def test_name(self):
        assert SkillberryPluginSkillsShImporter().metadata.name == "skills.sh Importer"

    def test_type(self):
        assert SkillberryPluginSkillsShImporter().metadata.plugin_type == PluginType.IMPORTER

    def test_version(self):
        assert SkillberryPluginSkillsShImporter().metadata.version == "0.1.0"

    def test_disabled_without_any_source(self):
        """Plugin is disabled only when NEITHER env var NOR .vercel/project.json exists."""
        plugin = SkillberryPluginSkillsShImporter()
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SKILLS_SH_TOKEN", None)
            with patch(
                "skillberry_plugin_skillssh_importer.plugin._has_token_source",
                return_value=False,
            ):
                assert not plugin.is_enabled()

    def test_enabled_with_env_token(self):
        plugin = SkillberryPluginSkillsShImporter()
        with patch.dict(os.environ, {"SKILLS_SH_TOKEN": "tok"}):
            assert plugin.is_enabled()

    def test_enabled_with_vercel_linked(self):
        """Plugin is enabled if .vercel/project.json is found even without env var."""
        plugin = SkillberryPluginSkillsShImporter()
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SKILLS_SH_TOKEN", None)
            with patch(
                "skillberry_plugin_skillssh_importer.plugin._has_token_source",
                return_value=True,
            ):
                assert plugin.is_enabled()

    def test_status_message_no_source(self):
        plugin = SkillberryPluginSkillsShImporter()
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SKILLS_SH_TOKEN", None)
            with patch(
                "skillberry_plugin_skillssh_importer.plugin._has_token_source",
                return_value=False,
            ):
                msg = plugin.get_status_message()
                assert msg.startswith("Disabled:")
                assert "vercel login" in msg.lower()
                assert "Option A" in msg
                assert "Option B" in msg

    def test_status_message_env_token(self):
        plugin = SkillberryPluginSkillsShImporter()
        with patch.dict(os.environ, {"SKILLS_SH_TOKEN": "tok"}):
            msg = plugin.get_status_message()
            assert msg.startswith("Ready")
            assert "SKILLS_SH_TOKEN" in msg

    def test_status_message_vercel_linked(self):
        plugin = SkillberryPluginSkillsShImporter()
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SKILLS_SH_TOKEN", None)
            with patch(
                "skillberry_plugin_skillssh_importer.plugin._has_token_source",
                return_value=True,
            ):
                msg = plugin.get_status_message()
                assert msg.startswith("Ready")
                assert "vercel" in msg.lower()


# ---------------------------------------------------------------------------
# Router structure
# ---------------------------------------------------------------------------

class TestRouterStructure:
    def test_has_search_and_import(self):
        plugin = SkillberryPluginSkillsShImporter()
        router = plugin.get_router()
        assert router is not None
        paths = [r.path for r in router.routes]
        assert any("search" in p for p in paths)
        assert any("import" in p for p in paths)

    def test_no_cli_commands(self):
        assert SkillberryPluginSkillsShImporter().get_cli_commands() is None

    # ── ui_config when ENABLED ───────────────────────────────────────────────

    def test_ui_config_enabled_has_two_actions(self):
        with patch(
            "skillberry_plugin_skillssh_importer.plugin._has_token_source",
            return_value=True,
        ):
            ui = SkillberryPluginSkillsShImporter().get_ui_config()
        assert ui is not None
        assert len(ui["actions"]) == 2

    def test_ui_config_enabled_color(self):
        with patch(
            "skillberry_plugin_skillssh_importer.plugin._has_token_source",
            return_value=True,
        ):
            ui = SkillberryPluginSkillsShImporter().get_ui_config()
        assert ui["color"] == "#0F766E"

    def test_ui_config_search_action(self):
        with patch(
            "skillberry_plugin_skillssh_importer.plugin._has_token_source",
            return_value=True,
        ):
            ui = SkillberryPluginSkillsShImporter().get_ui_config()
        search_action = next(a for a in ui["actions"] if "search" in a["endpoint"].lower())
        assert "query" in search_action["params_schema"]["properties"]
        assert "query" in search_action["params_schema"]["required"]

    def test_ui_config_import_action(self):
        with patch(
            "skillberry_plugin_skillssh_importer.plugin._has_token_source",
            return_value=True,
        ):
            ui = SkillberryPluginSkillsShImporter().get_ui_config()
        import_action = next(a for a in ui["actions"] if a["endpoint"].endswith("/import"))
        assert "skill_ids" in import_action["params_schema"]["properties"]
        assert "skill_ids" in import_action["params_schema"]["required"]

    # ── ui_config when DISABLED ──────────────────────────────────────────────

    def test_ui_config_disabled_has_no_actions(self):
        with patch(
            "skillberry_plugin_skillssh_importer.plugin._has_token_source",
            return_value=False,
        ):
            ui = SkillberryPluginSkillsShImporter().get_ui_config()
        assert ui["actions"] == []

    def test_ui_config_disabled_color_is_grey(self):
        with patch(
            "skillberry_plugin_skillssh_importer.plugin._has_token_source",
            return_value=False,
        ):
            ui = SkillberryPluginSkillsShImporter().get_ui_config()
        assert ui["color"] == "#6B7280"

    def test_ui_config_disabled_has_message(self):
        with patch(
            "skillberry_plugin_skillssh_importer.plugin._has_token_source",
            return_value=False,
        ):
            ui = SkillberryPluginSkillsShImporter().get_ui_config()
        assert "disabled_message" in ui
        assert "Disabled:" in ui["disabled_message"]

    def test_ui_config_disabled_has_setup_instructions(self):
        with patch(
            "skillberry_plugin_skillssh_importer.plugin._has_token_source",
            return_value=False,
        ):
            ui = SkillberryPluginSkillsShImporter().get_ui_config()
        si = ui["setup_instructions"]
        assert "title" in si
        assert len(si["steps"]) == 2
        assert "docs_url" in si
        assert si["docs_url"] == "https://skills.sh/docs/api#authentication"
        step_labels = [s["label"] for s in si["steps"]]
        assert any("Option A" in l for l in step_labels)
        assert any("Option B" in l for l in step_labels)


# ---------------------------------------------------------------------------
# /search endpoint
# ---------------------------------------------------------------------------

class TestSearchEndpoint:
    def test_missing_query_returns_422(self):
        client, _, _ = _make_client()
        resp = client.post("/plugins/skillssh-importer/search", json={})
        assert resp.status_code == 422

    def test_short_query_returns_422(self):
        """Query must be at least 2 characters (Pydantic min_length)."""
        client, _, _ = _make_client()
        resp = client.post("/plugins/skillssh-importer/search", json={"query": "x"})
        assert resp.status_code == 422

    def test_no_token_returns_400(self):
        client, _, _ = _make_client()
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SKILLS_SH_TOKEN", None)
            with patch(
                "skillberry_plugin_skillssh_importer.plugin._acquire_via_vercel_oidc",
                return_value=None,
            ):
                resp = client.post(
                    "/plugins/skillssh-importer/search",
                    json={"query": "react"},
                )
        assert resp.status_code == 400
        assert "token" in resp.json()["detail"].lower()

    def test_returns_normalized_items(self):
        mock_results = [
            {
                "id": "vercel-labs/skills/find-skills",
                "name": "find-skills",
                "source": "vercel-labs",
                "installs": 24531,
                "sourceType": "github",
                "installUrl": "https://skills.sh/install/find-skills",
                "url": "https://skills.sh/vercel-labs/skills/find-skills",
                "isDuplicate": True,
            }
        ]
        client, _, _ = _make_client()
        with patch(
            "skillberry_plugin_skillssh_importer.plugin.search_skills",
            return_value=mock_results,
        ):
            resp = client.post(
                "/plugins/skillssh-importer/search",
                json={"query": "find skills", "skills_sh_token": "tok"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert data["count"] == 1
        item = data["items"][0]
        assert item["id"] == "vercel-labs/skills/find-skills"
        assert item["title"] == "find-skills"
        assert item["subtitle"] == "vercel-labs/skills/find-skills"
        assert item["source"] == "vercel-labs"
        assert item["description"] is None
        # popover details are plugin-built; no raw skills.sh field names leak
        labels = {d["label"] for d in item["details"]}
        assert "Installs" in labels and "Source type" in labels
        assert any(d.get("href") for d in item["details"])
        assert item["badges"] == [{"label": "Duplicate", "color": "orange"}]

    def test_http_error_returns_502(self):
        import httpx

        client, _, _ = _make_client()
        with patch(
            "skillberry_plugin_skillssh_importer.plugin.search_skills",
            side_effect=Exception("Connection failed"),
        ):
            resp = client.post(
                "/plugins/skillssh-importer/search",
                json={"query": "something", "skills_sh_token": "tok"},
            )
        assert resp.status_code == 502


# ---------------------------------------------------------------------------
# /import endpoint
# ---------------------------------------------------------------------------

# Minimal stand-in objects to simulate the importer pipeline output
class _FakeTool:
    def __init__(self, name, description="", content=""):
        self.name = name
        self.description = description
        self.content = content
        self.source_file_name = f"{name}.py"
        self.params = {}
        self.language = "python"


class _FakeSnippet:
    def __init__(self, name, content=""):
        self.name = name
        self.content = content


def _patch_import(tools=None, snippets=None):
    """Patch import_skill_from_skillssh to return controlled data."""
    tools = tools or []
    snippets = snippets or []

    def _fake_import(skill_id, extra_tags=None, token=None, fetch_audits=True):
        return {
            "skill_name": skill_id.split("/")[-1],
            "skill_description": f"Imported from {skill_id}",
            "tools": tools,
            "snippets": snippets,
            "ignored_files": [],
            "tags": ["skills.sh", "installs:1k+"],
            "installs": 1234,
            "audits": [{"slug": "socket", "status": "pass"}],
            "skill_id": skill_id,
        }

    return patch(
        "skillberry_plugin_skillssh_importer.plugin.import_skill_from_skillssh",
        side_effect=_fake_import,
    )


class TestImportEndpoint:
    def test_empty_skill_ids_returns_422(self):
        client, _, _ = _make_client()
        resp = client.post(
            "/plugins/skillssh-importer/import",
            json={"skill_ids": []},
        )
        assert resp.status_code == 422

    def test_missing_skill_ids_returns_422(self):
        client, _, _ = _make_client()
        resp = client.post("/plugins/skillssh-importer/import", json={})
        assert resp.status_code == 422

    def test_successful_import_no_tools(self):
        client, _, mock_store = _make_client()
        with _patch_import(tools=[], snippets=[]):
            resp = client.post(
                "/plugins/skillssh-importer/import",
                json={"skill_ids": ["vercel-labs/skills/find-skills"], "skills_sh_token": "tok"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert len(body["data"]["imported"]) == 1
        item = body["data"]["imported"][0]
        assert item["title"] == "find-skills"
        assert item["id"] == "vercel-labs/skills/find-skills"
        assert "summary" in item

    def test_successful_import_with_tool(self):
        tools = [_FakeTool("echo", "Echo a message", "def echo(msg): return msg")]
        client, _, mock_store = _make_client()
        with _patch_import(tools=tools, snippets=[]):
            resp = client.post(
                "/plugins/skillssh-importer/import",
                json={"skill_ids": ["vercel-labs/skills/echo"], "skills_sh_token": "tok"},
            )
        assert resp.status_code == 200
        assert resp.json()["data"]["imported"][0]["tools_imported"] == 1
        mock_store.create_tool.assert_called_once()

    def test_successful_import_with_snippet(self):
        snippets = [_FakeSnippet("readme", "# Hello")]
        client, _, mock_store = _make_client()
        with _patch_import(tools=[], snippets=snippets):
            resp = client.post(
                "/plugins/skillssh-importer/import",
                json={"skill_ids": ["owner/repo/skill"], "skills_sh_token": "tok"},
            )
        assert resp.status_code == 200
        assert resp.json()["data"]["imported"][0]["snippets_imported"] == 1
        mock_store.create_snippet.assert_called_once()

    def test_tags_present_in_response(self):
        client, _, _ = _make_client()
        with _patch_import():
            resp = client.post(
                "/plugins/skillssh-importer/import",
                json={"skill_ids": ["owner/repo/skill"], "skills_sh_token": "tok"},
            )
        tags = resp.json()["data"]["imported"][0]["tags"]
        assert "skills.sh" in tags
        assert any("installs" in t for t in tags)

    def test_import_failure_lands_in_failed_list(self):
        client, _, _ = _make_client()
        with patch(
            "skillberry_plugin_skillssh_importer.plugin.import_skill_from_skillssh",
            side_effect=ValueError("Skill not found"),
        ):
            resp = client.post(
                "/plugins/skillssh-importer/import",
                json={"skill_ids": ["bad/skill/id"], "skills_sh_token": "tok"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert len(body["data"]["failed"]) == 1
        assert "bad/skill/id" in body["data"]["failed"][0]["id"]

    def test_partial_failure(self):
        """One skill fails, one succeeds — success=False, imported=1."""
        call_count = [0]

        def _side_effect(skill_id, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                raise ValueError("not found")
            return {
                "skill_name": "ok-skill",
                "skill_description": "ok",
                "tools": [],
                "snippets": [],
                "ignored_files": [],
                "tags": ["skills.sh"],
                "installs": 10,
                "audits": [],
                "skill_id": skill_id,
            }

        client, _, _ = _make_client()
        with patch(
            "skillberry_plugin_skillssh_importer.plugin.import_skill_from_skillssh",
            side_effect=_side_effect,
        ):
            resp = client.post(
                "/plugins/skillssh-importer/import",
                json={"skill_ids": ["bad/id", "good/id"], "skills_sh_token": "tok"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert len(body["data"]["imported"]) == 1
        assert len(body["data"]["failed"]) == 1

    def test_skill_creation_called_once_per_skill(self):
        client, _, mock_store = _make_client()
        with _patch_import(tools=[], snippets=[]):
            resp = client.post(
                "/plugins/skillssh-importer/import",
                json={
                    "skill_ids": ["a/b/c", "d/e/f"],
                    "skills_sh_token": "tok",
                },
            )
        assert resp.status_code == 200
        assert mock_store.create_skill.call_count == 2

    def test_audit_results_in_response(self):
        client, _, _ = _make_client()
        with _patch_import():
            resp = client.post(
                "/plugins/skillssh-importer/import",
                json={"skill_ids": ["owner/repo/skill"], "skills_sh_token": "tok"},
            )
        audits = resp.json()["data"]["imported"][0]["audits"]
        assert isinstance(audits, list)
        assert audits[0]["slug"] == "socket"

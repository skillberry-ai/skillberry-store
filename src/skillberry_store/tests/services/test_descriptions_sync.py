"""Integration tests: description index stays in sync with object population.

Each test creates real ObjectHandler (with vdb_type="faiss") and real Service
instances so that description writes, updates, and deletes go through the actual
FAISS-backed Description store.

Covered scenarios per service:
1. Create an object with a description → search returns it.
2. Update the description → search returns updated content.
3. Delete the object → search no longer returns it.
4. Create two objects, delete one → search returns only the surviving one.
"""

import pytest
from unittest.mock import patch
from skillberry_store.modules.object_handler import ObjectHandler
from skillberry_store.services.snippets_service import SnippetsService
from skillberry_store.services.tools_service import ToolsService
from skillberry_store.services.skills_service import SkillsService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def snippet_handler(tmp_path):
    """Real ObjectHandler for snippets backed by a temporary directory."""
    return ObjectHandler(str(tmp_path / "snippets"), "snippet", vdb_type="faiss")


@pytest.fixture()
def tool_handler(tmp_path):
    """Real ObjectHandler for tools backed by a temporary directory."""
    return ObjectHandler(str(tmp_path / "tools"), "tool", vdb_type="faiss")


@pytest.fixture()
def skill_handler(tmp_path):
    """Real ObjectHandler for skills backed by a temporary directory."""
    return ObjectHandler(str(tmp_path / "skills"), "skill", vdb_type="faiss")


def _search_names(service, term: str) -> list[str]:
    """Return the list of names for the UUIDs returned by service.search() for *term*."""
    results = service.search(term, max_number_of_results=10, similarity_threshold=100.0)
    names = []
    for r in results:
        try:
            names.append(service.get(r["uuid"]).get("name", ""))
        except Exception:
            pass
    return names


# ---------------------------------------------------------------------------
# SnippetsService integration tests
# ---------------------------------------------------------------------------

class TestSnippetDescriptionsSync:

    def test_create_makes_snippet_searchable(self, snippet_handler):
        svc = SnippetsService(snippet_handler)
        svc.create({"name": "alpha", "content": "x", "description": "quantum entanglement physics"})
        names = _search_names(svc, "quantum entanglement")
        assert "alpha" in names

    def test_update_description_is_reflected_in_search(self, snippet_handler):
        svc = SnippetsService(snippet_handler)
        svc.create({"name": "beta", "content": "x", "description": "classical mechanics"})
        svc.update("beta", {"description": "quantum field theory"})
        # new term finds the snippet
        names = _search_names(svc, "quantum field theory")
        assert "beta" in names

    def test_delete_removes_snippet_from_search(self, snippet_handler):
        svc = SnippetsService(snippet_handler)
        svc.create({"name": "gamma", "content": "x", "description": "solar panel efficiency"})
        # Confirm it is searchable before deletion
        assert "gamma" in _search_names(svc, "solar panel")
        svc.delete("gamma")
        # After deletion it must not appear
        assert "gamma" not in _search_names(svc, "solar panel")

    def test_delete_one_keeps_other_searchable(self, snippet_handler):
        svc = SnippetsService(snippet_handler)
        svc.create({"name": "keep", "content": "x", "description": "machine learning neural network"})
        svc.create({"name": "drop", "content": "x", "description": "machine learning neural network"})
        svc.delete("drop")
        names = _search_names(svc, "machine learning")
        assert "keep" in names
        assert "drop" not in names


# ---------------------------------------------------------------------------
# ToolsService integration tests
# ---------------------------------------------------------------------------

class TestToolDescriptionsSync:

    def _create_tool(self, svc: ToolsService, name: str, description: str):
        return svc.create(
            {"name": name, "description": description},
            module_content=b"def run(): pass",
            module_filename=f"{name}.py",
        )

    def test_create_makes_tool_searchable(self, tool_handler):
        svc = ToolsService(tool_handler)
        self._create_tool(svc, "fetch_weather", "retrieve current weather data from API")
        names = _search_names(svc, "weather data API")
        assert "fetch_weather" in names

    def test_update_description_is_reflected_in_search(self, tool_handler):
        svc = ToolsService(tool_handler)
        self._create_tool(svc, "calc_sum", "add two integers together")
        svc.update("calc_sum", {"description": "compute fibonacci sequence"})
        names = _search_names(svc, "fibonacci sequence")
        assert "calc_sum" in names

    def test_delete_removes_tool_from_search(self, tool_handler):
        svc = ToolsService(tool_handler)
        self._create_tool(svc, "send_email", "send email via SMTP protocol")
        assert "send_email" in _search_names(svc, "email SMTP")
        svc.delete("send_email")
        assert "send_email" not in _search_names(svc, "email SMTP")

    def test_delete_one_keeps_other_searchable(self, tool_handler):
        svc = ToolsService(tool_handler)
        self._create_tool(svc, "tool_keep", "parse JSON configuration files")
        self._create_tool(svc, "tool_drop", "parse JSON configuration files")
        svc.delete("tool_drop")
        names = _search_names(svc, "JSON configuration")
        assert "tool_keep" in names
        assert "tool_drop" not in names


# ---------------------------------------------------------------------------
# SkillsService integration tests
# ---------------------------------------------------------------------------

class TestSkillDescriptionsSync:
    """Uses a patched registry so SkillsService.create/update/delete can call
    get_service("tool") and get_service("snippet") without a full server setup."""

    @pytest.fixture()
    def skill_svc(self, skill_handler):
        mock_sibling = _make_noop_sibling()
        with patch(
            "skillberry_store.services.registry.get_service",
            return_value=mock_sibling,
        ):
            yield SkillsService(skill_handler)

    def test_create_makes_skill_searchable(self, skill_svc):
        skill_svc.create({"name": "sky_skill", "description": "orchestrate cloud deployment pipeline"})
        names = _search_names(skill_svc, "cloud deployment")
        assert "sky_skill" in names

    def test_update_description_is_reflected_in_search(self, skill_svc):
        skill_svc.create({"name": "data_skill", "description": "perform ETL data transformation"})
        skill_svc.update("data_skill", {"description": "train machine learning model"})
        names = _search_names(skill_svc, "machine learning model")
        assert "data_skill" in names

    def test_delete_removes_skill_from_search(self, skill_svc):
        skill_svc.create({"name": "net_skill", "description": "monitor network bandwidth usage"})
        assert "net_skill" in _search_names(skill_svc, "network bandwidth")
        skill_svc.delete("net_skill")
        assert "net_skill" not in _search_names(skill_svc, "network bandwidth")

    def test_delete_one_keeps_other_searchable(self, skill_svc):
        skill_svc.create({"name": "skill_keep", "description": "analyse stock market trends"})
        skill_svc.create({"name": "skill_drop", "description": "analyse stock market trends"})
        skill_svc.delete("skill_drop")
        names = _search_names(skill_svc, "stock market")
        assert "skill_keep" in names
        assert "skill_drop" not in names


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_noop_sibling():
    """Return a minimal mock for sibling services (tool/snippet) used by SkillsService."""
    from unittest.mock import MagicMock
    sibling = MagicMock()
    sibling.add_dependent.return_value = None
    sibling.remove_dependent.return_value = None
    return sibling

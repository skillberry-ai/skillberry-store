"""Tests for the Creator Plugin (SDK-based)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from skillberry_plugin_creator.plugin import SkillberryPluginCreator


# ── manifest ──────────────────────────────────────────────────────────────────

def test_plugin_manifest_slug():
    plugin = SkillberryPluginCreator()
    assert plugin.manifest.slug == "creator"


def test_plugin_manifest_type_creator():
    plugin = SkillberryPluginCreator()
    assert plugin.manifest.plugin_type == "creator"


def test_plugin_manifest_version():
    plugin = SkillberryPluginCreator()
    assert plugin.manifest.version == "0.1.0"


def test_plugin_manifest_has_api():
    plugin = SkillberryPluginCreator()
    assert plugin.manifest.has_api is True


def test_plugin_manifest_description_mentions_create():
    plugin = SkillberryPluginCreator()
    assert "create" in plugin.manifest.description.lower()


# ── lifecycle: on_start ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_on_start_disabled_when_llm_unavailable():
    mock_module = MagicMock()
    mock_module.get_llm.side_effect = RuntimeError("LLM unavailable")
    with patch.dict("sys.modules", {"llm_switchboard": mock_module}):
        plugin = SkillberryPluginCreator()
        await plugin.on_start()
        assert not plugin.is_enabled()


@pytest.mark.asyncio
async def test_on_start_enabled_when_llm_available():
    mock_client = MagicMock()
    mock_llm_class = MagicMock(return_value=mock_client)
    mock_module = MagicMock()
    mock_module.get_llm.return_value = mock_llm_class
    with patch.dict("sys.modules", {"llm_switchboard": mock_module}):
        plugin = SkillberryPluginCreator()
        await plugin.on_start()
        assert plugin.is_enabled()


# ── is_ready ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_is_ready_true_when_llm_initialized():
    plugin = SkillberryPluginCreator()
    plugin.llm_client = MagicMock()
    result = await plugin.is_ready()
    assert result["ready"] is True
    assert result["missing_config"] == []


@pytest.mark.asyncio
async def test_is_ready_false_when_llm_missing():
    plugin = SkillberryPluginCreator()
    plugin.llm_client = None
    plugin._status_message = "Missing dependency"
    result = await plugin.is_ready()
    assert result["ready"] is False
    assert result["missing_config"]


# ── router ────────────────────────────────────────────────────────────────────

def test_plugin_provides_router():
    plugin = SkillberryPluginCreator()
    router = plugin.get_router()

    assert router is not None
    route_paths = [route.path for route in router.routes]
    assert any("create" in path for path in route_paths)


# ── create_snippet ────────────────────────────────────────────────────────────

def _plugin_with_store_and_llm(created_snippet=None, content="print('hello')",
                                metadata_json='{"language":"python","tags":["hello"],"description":"say hi"}'):
    """Return a plugin with mocked store + llm client."""
    plugin = SkillberryPluginCreator()

    llm = MagicMock()
    llm.generate_async = AsyncMock(side_effect=[content, metadata_json])
    plugin.llm_client = llm

    store = AsyncMock()
    if created_snippet is None:
        created_snippet = {"uuid": "snip-1", "name": "generated", "content": content}
    store.post = AsyncMock(return_value=created_snippet)
    plugin._store = store
    return plugin, store, llm


@pytest.mark.asyncio
async def test_create_snippet_calls_store_post_snippets():
    plugin, store, _ = _plugin_with_store_and_llm()
    await plugin.create_snippet("print hello in python")
    store.post.assert_awaited_once()
    path = store.post.call_args[0][0]
    assert path == "/snippets/"


@pytest.mark.asyncio
async def test_create_snippet_returns_created_snippet():
    created = {"uuid": "snip-42", "name": "hello", "content": "print('hi')"}
    plugin, _, _ = _plugin_with_store_and_llm(created_snippet=created)
    result = await plugin.create_snippet("print hello")
    assert result == created


@pytest.mark.asyncio
async def test_create_snippet_uses_provided_name():
    plugin, store, _ = _plugin_with_store_and_llm()
    await plugin.create_snippet("print hello", name="my-snippet")
    payload = store.post.call_args.kwargs["json"]
    assert payload["name"] == "my-snippet"


@pytest.mark.asyncio
async def test_create_snippet_infers_metadata_from_llm():
    plugin, store, _ = _plugin_with_store_and_llm()
    await plugin.create_snippet("print hello")
    payload = store.post.call_args.kwargs["json"]
    assert payload["language"] == "python"
    assert "hello" in payload["tags"]


@pytest.mark.asyncio
async def test_create_snippet_falls_back_when_metadata_unparseable():
    plugin, store, _ = _plugin_with_store_and_llm(metadata_json="not json at all")
    await plugin.create_snippet("print hello")
    payload = store.post.call_args.kwargs["json"]
    assert payload["language"] == "text"


@pytest.mark.asyncio
async def test_create_snippet_raises_when_llm_missing():
    plugin = SkillberryPluginCreator()
    plugin.llm_client = None
    with pytest.raises(RuntimeError, match="LLM client"):
        await plugin.create_snippet("x")


@pytest.mark.asyncio
async def test_create_snippet_raises_when_store_missing():
    plugin = SkillberryPluginCreator()
    plugin.llm_client = MagicMock()
    plugin._store = None
    with pytest.raises(RuntimeError, match="Store"):
        await plugin.create_snippet("x")

"""Tests for the LLM generation path: prompt building, JSON parsing, mode.

No real LLM is contacted: the switchboard module is faked at import time (so the
plugin builds a mock client, exactly like the security plugin's tests) and
``generate_async`` is stubbed with an ``AsyncMock``.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from skillberry_plugin_doc_generator.models import (
    MODE_ENRICHED,
    MODE_GENERATED,
    MODE_KEPT,
    ObjectDoc,
    ParamDoc,
)
from skillberry_plugin_doc_generator.plugin import SkillberryPluginDocGenerator


def _make_plugin_with_mock_llm():
    """Create a plugin instance with a mocked (enabled) LLM client."""
    mock_client = MagicMock()
    mock_llm_class = MagicMock(return_value=mock_client)
    mock_module = MagicMock()
    mock_module.get_llm.return_value = mock_llm_class
    with patch.dict("sys.modules", {"llm_switchboard": mock_module}):
        plugin = SkillberryPluginDocGenerator()
    return plugin


def _obj(description="", tags=None, parameters=None, code_blobs=None):
    return ObjectDoc(
        object_type="tool",
        uuid="t1",
        name="send_msg",
        description=description,
        tags=list(tags or []),
        parameters=list(parameters or []),
        code_blobs=list(code_blobs or []),
    )


# ── prompt building ──────────────────────────────────────────────────────────


def test_build_prompt_includes_params_code_and_contract():
    obj = _obj(
        description="Sends a message",
        tags=["messaging"],
        parameters=[ParamDoc(name="channel", type="string", required=True)],
        code_blobs=["import requests"],
    )
    prompt = SkillberryPluginDocGenerator._build_prompt(obj, None)
    assert "send_msg" in prompt
    assert "Sends a message" in prompt  # author description carried in
    assert "channel" in prompt
    assert "import requests" in prompt
    # the JSON output contract is spelled out
    assert '"when_to_use"' in prompt
    assert "ONLY the JSON object" in prompt


# ── JSON parsing ─────────────────────────────────────────────────────────────


def test_parse_documentation_extracts_json_from_noisy_response():
    payload = {
        "description": "Sends a message via the API.",
        "when_to_use": "When you need to notify a channel.",
        "parameters": [
            {
                "name": "channel",
                "type": "string",
                "required": True,
                "description": "target",
            }
        ],
        "examples": ["send_msg(channel='general')"],
    }
    response = "Here is the JSON:\n" + json.dumps(payload) + "\nThanks!"
    doc = SkillberryPluginDocGenerator._parse_documentation(response)
    assert doc.description == "Sends a message via the API."
    assert doc.when_to_use.startswith("When you need")
    assert [p.name for p in doc.parameters] == ["channel"]
    assert doc.examples == ["send_msg(channel='general')"]


def test_parse_documentation_raises_on_no_json():
    with pytest.raises(RuntimeError, match="Failed to parse"):
        SkillberryPluginDocGenerator._parse_documentation("no json at all")


def test_parse_documentation_skips_malformed_params():
    response = json.dumps(
        {"description": "d", "parameters": [{"type": "string"}, {"name": "ok"}]}
    )
    doc = SkillberryPluginDocGenerator._parse_documentation(response)
    assert [p.name for p in doc.parameters] == ["ok"]  # nameless entry dropped


# ── mode classification ──────────────────────────────────────────────────────


def test_classify_mode_by_author_description():
    cls = SkillberryPluginDocGenerator._classify_mode
    assert cls("") == MODE_GENERATED
    assert cls("Gets data") == MODE_ENRICHED  # thin (< 40 chars)
    assert cls("x" * 80) == MODE_KEPT


# ── end-to-end generation (mocked client) ────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_documentation_labels_and_keeps_author_content():
    plugin = _make_plugin_with_mock_llm()
    plugin.llm_client.generate_async = AsyncMock(
        return_value=json.dumps(
            {
                "description": "LLM rewrote this much longer description.",
                "when_to_use": "Whenever.",
                "examples": ["use it"],
            }
        )
    )
    author = "A sufficiently long, author-written description of the tool's job."
    doc = await plugin._generate_documentation(_obj(description=author), None)
    # substantial author content -> kept verbatim (non-destructive)
    assert doc.mode == MODE_KEPT
    assert doc.description == author


@pytest.mark.asyncio
async def test_generate_documentation_raises_on_empty_response():
    plugin = _make_plugin_with_mock_llm()
    plugin.llm_client.generate_async = AsyncMock(return_value="{}")
    with pytest.raises(RuntimeError, match="empty documentation"):
        await plugin._generate_documentation(_obj(), None)


@pytest.mark.asyncio
async def test_generate_documentation_raises_on_bad_response():
    plugin = _make_plugin_with_mock_llm()
    plugin.llm_client.generate_async = AsyncMock(return_value="not json")
    with pytest.raises(RuntimeError, match="Failed to parse"):
        await plugin._generate_documentation(_obj(), None)

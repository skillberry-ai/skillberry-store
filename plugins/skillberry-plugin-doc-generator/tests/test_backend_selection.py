"""Tests for env-driven backend selection and the optional LLM backend.

No real LLM is contacted: ``build_llm_client`` is monkeypatched and the
switchboard client is faked. These verify the policy you asked for —
default stays deterministic; an LLM is used only when one is available.
"""

import json

from skillberry_plugin_doc_generator.generators import resolve_generator
from skillberry_plugin_doc_generator.generators.base import ObjectDoc
from skillberry_plugin_doc_generator.generators.heuristic import HeuristicGenerator

# ── selection policy ─────────────────────────────────────────────────────────


def test_default_is_heuristic_when_no_llm(monkeypatch):
    # No LLM configured -> build returns None -> heuristic.
    monkeypatch.setattr(
        "skillberry_plugin_doc_generator.generators.llm.build_llm_client",
        lambda: None,
    )
    assert resolve_generator(None).name == "heuristic"
    assert resolve_generator("auto").name == "heuristic"


def test_force_heuristic_ignores_llm(monkeypatch):
    monkeypatch.setattr(
        "skillberry_plugin_doc_generator.generators.llm.build_llm_client",
        lambda: ("client", "x:y"),
    )
    assert resolve_generator("heuristic").name == "heuristic"


def test_llm_selected_when_available(monkeypatch):
    class _FakeClient:
        async def generate_async(self, prompt):
            return "{}"

    monkeypatch.setattr(
        "skillberry_plugin_doc_generator.generators.llm.build_llm_client",
        lambda: (_FakeClient(), "openai.async:gpt-4"),
    )
    gen = resolve_generator("auto")
    assert gen.name.startswith("llm(")
    assert "gpt-4" in gen.name


def test_unknown_name_falls_back_to_heuristic():
    assert resolve_generator("bogus").name == "heuristic"


def test_build_llm_client_gated_on_api_key(monkeypatch):
    """No key for the configured provider -> no client (heuristic default)."""
    from skillberry_plugin_doc_generator.generators import llm as llm_mod

    monkeypatch.setenv("LLM_PROVIDER", "openai.async")
    for var in ("LLM_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    assert llm_mod.build_llm_client() is None

    # With a key present, construction is attempted (get_llm is faked here).
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(
        llm_mod,
        "get_llm",
        lambda provider: (lambda model_name: object()),
        raising=False,
    )
    # Patch the import target used inside build_llm_client.
    import types

    fake = types.SimpleNamespace(get_llm=lambda provider: (lambda model_name: object()))
    monkeypatch.setitem(__import__("sys").modules, "llm_switchboard", fake)
    built = llm_mod.build_llm_client()
    assert built is not None
    _, label = built
    assert "openai.async" in label


def test_explicit_llm_api_key_counts(monkeypatch):
    from skillberry_plugin_doc_generator.generators import llm as llm_mod

    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("LLM_API_KEY", "generic-key")
    assert llm_mod._has_api_key("anthropic") is True


# ── LLM backend behavior ─────────────────────────────────────────────────────


def _obj():
    return ObjectDoc(
        object_type="tool",
        uuid="t1",
        name="send_msg",
        code_blobs=["import requests"],
    )


def test_llm_generator_parses_json_response():
    from skillberry_plugin_doc_generator.generators.llm import LLMGenerator

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

    class _Client:
        async def generate_async(self, prompt):
            return "Here is the JSON:\n" + json.dumps(payload) + "\nThanks!"

    doc = LLMGenerator(_Client(), "fake:model").generate(_obj(), None)
    assert doc.description == "Sends a message via the API."
    assert doc.when_to_use.startswith("When you need")
    assert [p.name for p in doc.parameters] == ["channel"]
    assert doc.examples == ["send_msg(channel='general')"]


def test_llm_generator_falls_back_to_heuristic_on_error():
    from skillberry_plugin_doc_generator.generators.llm import LLMGenerator

    class _BrokenClient:
        async def generate_async(self, prompt):
            raise RuntimeError("model unavailable")

    gen = LLMGenerator(_BrokenClient(), "fake:model")
    doc = gen.generate(_obj(), None)
    # Falls back to a real heuristic result (non-empty), not an exception.
    heuristic = HeuristicGenerator().generate(_obj(), None)
    assert doc.description == heuristic.description
    assert not doc.is_empty()


def test_llm_generator_falls_back_on_empty_response():
    from skillberry_plugin_doc_generator.generators.llm import LLMGenerator

    class _EmptyClient:
        async def generate_async(self, prompt):
            return "{}"  # parses, but yields empty documentation

    doc = LLMGenerator(_EmptyClient(), "fake:model").generate(_obj(), None)
    assert not doc.is_empty()  # heuristic fallback kicked in

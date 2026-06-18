"""Unit tests for the deterministic documentation generator (no network/LLM)."""

from skillberry_plugin_doc_generator.generators import (
    Documentation,
    HeuristicGenerator,
    ObjectDoc,
    ParamDoc,
    resolve_generator,
)
from skillberry_plugin_doc_generator.generators.base import (
    MODE_ENRICHED,
    MODE_GENERATED,
    MODE_KEPT,
)


def _gen():
    return HeuristicGenerator()


def test_resolve_generator_defaults_to_heuristic():
    assert resolve_generator().name == "heuristic"
    assert resolve_generator("unknown-backend").name == "heuristic"


def test_generate_tool_from_scratch():
    obj = ObjectDoc(
        object_type="tool",
        uuid="t1",
        name="send_slack_message",
        parameters=[
            ParamDoc(name="channel", type="string", required=True),
            ParamDoc(name="text", type="string", required=True),
        ],
        code_blobs=["import requests\nrequests.post(url)"],
    )
    doc = _gen().generate(obj, None)

    assert doc.mode == MODE_GENERATED
    assert "Send slack message" in doc.description
    assert "network" in doc.description  # inferred from requests
    assert doc.when_to_use
    assert [p.name for p in doc.parameters] == ["channel", "text"]
    # required params drive the example signature
    assert doc.examples and "send_slack_message(" in doc.examples[0]
    assert "channel=..." in doc.examples[0]


def test_good_author_description_is_kept_verbatim():
    obj = ObjectDoc(
        object_type="tool",
        uuid="t2",
        name="x",
        description=(
            "Posts a richly formatted message to a Slack channel and returns "
            "the message timestamp for threading."
        ),
    )
    doc = _gen().generate(obj, None)
    assert doc.mode == MODE_KEPT
    assert doc.description == obj.description


def test_thin_author_description_is_enriched_not_discarded():
    obj = ObjectDoc(
        object_type="tool",
        uuid="t3",
        name="fetch",
        description="Gets data",  # thin (< 40 chars)
        code_blobs=["import httpx"],
    )
    doc = _gen().generate(obj, None)
    assert doc.mode == MODE_ENRICHED
    assert doc.description.startswith("Gets data")  # author content preserved
    assert "network" in doc.description  # enrichment added


def test_parameter_descriptions_filled_when_missing():
    obj = ObjectDoc(
        object_type="tool",
        uuid="t4",
        name="t",
        parameters=[ParamDoc(name="limit", type="integer", required=False)],
    )
    doc = _gen().generate(obj, None)
    assert len(doc.parameters) == 1
    p = doc.parameters[0]
    assert p.name == "limit"
    assert "Optional" in p.description and "limit" in p.description


def test_tool_without_params_notes_the_gap():
    obj = ObjectDoc(object_type="tool", uuid="t5", name="t", code_blobs=["x = 1"])
    doc = _gen().generate(obj, None)
    assert any("parameter schema" in n for n in doc.notes)


def test_skill_mentions_references():
    obj = ObjectDoc(
        object_type="skill",
        uuid="s1",
        name="invoice_pipeline",
        references=["tool:ocr", "snippet:prompt"],
    )
    doc = _gen().generate(obj, None)
    assert "2 referenced object(s)" in doc.description
    assert doc.examples and "invoice_pipeline" in doc.examples[0]


def test_snippet_generation():
    obj = ObjectDoc(
        object_type="snippet",
        uuid="sn1",
        name="retry_prompt",
        code_blobs=["You are a careful assistant."],
    )
    doc = _gen().generate(obj, None)
    assert "Retry prompt" in doc.description
    assert doc.examples and "retry_prompt" in doc.examples[0]


def test_documentation_to_dict_roundtrip_shape():
    doc = Documentation(
        description="d",
        when_to_use="w",
        parameters=[ParamDoc(name="a", type="string", required=True, description="x")],
        examples=["e"],
    )
    d = doc.to_dict()
    assert set(d) == {
        "description",
        "when_to_use",
        "parameters",
        "examples",
        "mode",
        "notes",
    }
    assert d["parameters"][0] == {
        "name": "a",
        "type": "string",
        "required": True,
        "description": "x",
    }


def test_source_fingerprint_changes_with_code_but_not_author_desc():
    a = ObjectDoc(object_type="tool", uuid="t", name="t", code_blobs=["v1"])
    b = ObjectDoc(object_type="tool", uuid="t", name="t", code_blobs=["v2"])
    same_code_diff_desc = ObjectDoc(
        object_type="tool", uuid="t", name="t", code_blobs=["v1"], description="new"
    )
    assert a.source_fingerprint() != b.source_fingerprint()
    # author description is intentionally excluded from the fingerprint
    assert a.source_fingerprint() == same_code_diff_desc.source_fingerprint()

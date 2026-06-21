"""Unit tests for the documentation data shapes (no network/LLM)."""

from skillberry_plugin_doc_generator.models import (
    Documentation,
    ObjectDoc,
    ParamDoc,
)


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


def test_documentation_is_empty():
    assert Documentation().is_empty()
    assert not Documentation(description="something").is_empty()


def test_source_fingerprint_changes_with_code_but_not_author_desc():
    a = ObjectDoc(object_type="tool", uuid="t", name="t", code_blobs=["v1"])
    b = ObjectDoc(object_type="tool", uuid="t", name="t", code_blobs=["v2"])
    same_code_diff_desc = ObjectDoc(
        object_type="tool", uuid="t", name="t", code_blobs=["v1"], description="new"
    )
    assert a.source_fingerprint() != b.source_fingerprint()
    # author description is intentionally excluded from the fingerprint
    assert a.source_fingerprint() == same_code_diff_desc.source_fingerprint()


def test_source_fingerprint_changes_with_parameters():
    a = ObjectDoc(
        object_type="tool",
        uuid="t",
        name="t",
        parameters=[ParamDoc(name="a", type="string", required=True)],
    )
    b = ObjectDoc(
        object_type="tool",
        uuid="t",
        name="t",
        parameters=[
            ParamDoc(name="a", type="string", required=True),
            ParamDoc(name="b", type="int", required=False),
        ],
    )
    assert a.source_fingerprint() != b.source_fingerprint()

import pytest

from skillberry_store.schemas.manifest_schema import ManifestSchema
from skillberry_store.schemas.snippet_schema import SnippetSchema
from skillberry_store.utils.python_utils import extract_docstring


def test_manifest_extra_accepts_json_object_string():
    manifest = ManifestSchema(
        name="snippet",
        extra='{"recommendation_key": "prompt_change"}',
    )

    assert manifest.extra == {"recommendation_key": "prompt_change"}


def test_snippet_extra_accepts_json_object_string():
    snippet = SnippetSchema(
        name="prompt_snippet",
        content="Use explicit confirmation.",
        extra='{"recommendation_key": "prompt_change"}',
    )

    assert snippet.extra == {"recommendation_key": "prompt_change"}


def test_manifest_extra_rejects_non_object_json_string():
    with pytest.raises(ValueError, match="extra must be a dictionary"):
        ManifestSchema(name="snippet", extra='["not", "a", "dict"]')


def test_extract_docstring_fills_missing_params_from_signature():
    code = b'''
from typing import Any, Dict, List

def batch_get_reservation_details(reservation_ids: List[str]) -> Dict[str, Any]:
    """Fetch reservation details. Parameters: reservation_ids (List[str]): list of IDs. Returns: Dict[str, Any]: result."""
    return {"reservations": [], "errors": []}
'''

    function_name, docstring_obj = extract_docstring(
        code,
        selected_func="batch_get_reservation_details",
    )

    assert function_name == "batch_get_reservation_details"
    assert docstring_obj.params[0].arg_name == "reservation_ids"
    assert docstring_obj.params[0].type_name == "List[str]"

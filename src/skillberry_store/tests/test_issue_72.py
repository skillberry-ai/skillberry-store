# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0

"""Regression tests for issue #72."""

from skillberry_store.utils.python_utils import extract_docstring


def test_extract_docstring_preserves_signature_order_for_missing_params():
    code = b'''
from typing import Any, Dict

def create_order(
    customer_id: str,
    quantity: int,
    expedited: bool = False,
) -> Dict[str, Any]:
    """
    Create an order.

    Parameters:
        customer_id (str): 888
    Returns:
        Dict[str, Any]: Created order details.
    """
    return {"ok": True}
'''

    function_name, docstring_obj = extract_docstring(
        code,
        tool_name="create_order",
    )

    assert function_name == "create_order"
    assert [param.arg_name for param in docstring_obj.params] == [
        "customer_id",
        "quantity",
        "expedited",
    ]
    assert docstring_obj.params[1].type_name == "int"
    assert docstring_obj.params[2].type_name == "bool"
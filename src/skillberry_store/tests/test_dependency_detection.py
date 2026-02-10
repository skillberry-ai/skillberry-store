"""Tests for automatic tool dependency detection."""

import pytest
from skillberry_store.modules.file_executor import detect_tool_dependencies


class TestDependencyDetection:
    """Test suite for automatic dependency detection from Python code."""

    def test_detect_single_dependency(self):
        """Test detection of a single function call dependency."""
        code = """
def my_tool(user_id: str):
    '''My tool that uses get_user_details'''
    user = get_user_details(user_id)
    return user
"""
        available_tools = ["get_user_details", "other_tool", "another_tool"]
        
        dependencies = detect_tool_dependencies(code, "my_tool", available_tools)
        
        assert len(dependencies) == 1
        assert "get_user_details" in dependencies

    def test_detect_multiple_dependencies(self):
        """Test detection of multiple function call dependencies."""
        code = """
def process_user(user_id: str):
    '''Process user with multiple dependencies'''
    user = get_user_details(user_id)
    profile = get_user_profile(user_id)
    settings = get_user_settings(user_id)
    return {"user": user, "profile": profile, "settings": settings}
"""
        available_tools = [
            "get_user_details",
            "get_user_profile", 
            "get_user_settings",
            "unrelated_tool"
        ]
        
        dependencies = detect_tool_dependencies(code, "process_user", available_tools)
        
        assert len(dependencies) == 3
        assert "get_user_details" in dependencies
        assert "get_user_profile" in dependencies
        assert "get_user_settings" in dependencies
        assert "unrelated_tool" not in dependencies

    def test_no_dependencies(self):
        """Test function with no dependencies."""
        code = """
def simple_tool(x: int, y: int):
    '''Simple tool with no dependencies'''
    return x + y
"""
        available_tools = ["get_user_details", "other_tool"]
        
        dependencies = detect_tool_dependencies(code, "simple_tool", available_tools)
        
        assert len(dependencies) == 0

    def test_ignore_builtin_functions(self):
        """Test that built-in functions are not detected as dependencies."""
        code = """
def my_tool(items: list):
    '''Tool using built-in functions'''
    result = len(items)
    sorted_items = sorted(items)
    return {"count": result, "sorted": sorted_items}
"""
        available_tools = ["len", "sorted", "get_user_details"]
        
        dependencies = detect_tool_dependencies(code, "my_tool", available_tools)
        
        # len and sorted should be detected if they're in available_tools
        # This tests that we match against available_tools list
        assert "len" in dependencies
        assert "sorted" in dependencies
        assert "get_user_details" not in dependencies

    def test_ignore_unavailable_functions(self):
        """Test that functions not in available_tools are ignored."""
        code = """
def my_tool(user_id: str):
    '''Tool calling unavailable function'''
    user = get_user_details(user_id)
    data = unavailable_function(user)
    return data
"""
        available_tools = ["get_user_details"]
        
        dependencies = detect_tool_dependencies(code, "my_tool", available_tools)
        
        assert len(dependencies) == 1
        assert "get_user_details" in dependencies
        assert "unavailable_function" not in dependencies

    def test_method_calls(self):
        """Test detection of method calls (attribute access)."""
        code = """
def my_tool(obj):
    '''Tool with method calls'''
    result = obj.process_data()
    return result
"""
        available_tools = ["process_data", "other_tool"]
        
        dependencies = detect_tool_dependencies(code, "my_tool", available_tools)
        
        assert "process_data" in dependencies

    def test_nested_function_calls(self):
        """Test detection in nested function calls."""
        code = """
def my_tool(user_id: str):
    '''Tool with nested calls'''
    result = process_result(get_user_details(user_id))
    return result
"""
        available_tools = ["get_user_details", "process_result"]
        
        dependencies = detect_tool_dependencies(code, "my_tool", available_tools)
        
        assert len(dependencies) == 2
        assert "get_user_details" in dependencies
        assert "process_result" in dependencies

    def test_duplicate_calls_counted_once(self):
        """Test that duplicate function calls are only counted once."""
        code = """
def my_tool(user_id: str):
    '''Tool calling same function multiple times'''
    user1 = get_user_details(user_id)
    user2 = get_user_details(user_id)
    user3 = get_user_details(user_id)
    return [user1, user2, user3]
"""
        available_tools = ["get_user_details"]
        
        dependencies = detect_tool_dependencies(code, "my_tool", available_tools)
        
        assert len(dependencies) == 1
        assert "get_user_details" in dependencies

    def test_wrong_function_name(self):
        """Test with non-existent function name."""
        code = """
def my_tool(x: int):
    '''My tool'''
    return x * 2
"""
        available_tools = ["get_user_details"]
        
        dependencies = detect_tool_dependencies(code, "nonexistent_function", available_tools)
        
        assert len(dependencies) == 0

    def test_syntax_error_handling(self):
        """Test handling of syntax errors in code."""
        code = """
def my_tool(x: int)
    '''Missing colon'''
    return x * 2
"""
        available_tools = ["get_user_details"]
        
        dependencies = detect_tool_dependencies(code, "my_tool", available_tools)
        
        # Should return empty list on syntax error
        assert len(dependencies) == 0

    def test_conditional_calls(self):
        """Test detection of calls in conditional blocks."""
        code = """
def my_tool(user_id: str, include_profile: bool):
    '''Tool with conditional calls'''
    user = get_user_details(user_id)
    if include_profile:
        profile = get_user_profile(user_id)
        return {"user": user, "profile": profile}
    return {"user": user}
"""
        available_tools = ["get_user_details", "get_user_profile"]
        
        dependencies = detect_tool_dependencies(code, "my_tool", available_tools)
        
        assert len(dependencies) == 2
        assert "get_user_details" in dependencies
        assert "get_user_profile" in dependencies

    def test_loop_calls(self):
        """Test detection of calls in loops."""
        code = """
def my_tool(user_ids: list):
    '''Tool with loop calls'''
    results = []
    for user_id in user_ids:
        user = get_user_details(user_id)
        results.append(user)
    return results
"""
        available_tools = ["get_user_details"]
        
        dependencies = detect_tool_dependencies(code, "my_tool", available_tools)
        
        assert len(dependencies) == 1
        assert "get_user_details" in dependencies

    def test_lambda_calls(self):
        """Test detection of calls in lambda functions."""
        code = """
def my_tool(user_ids: list):
    '''Tool with lambda'''
    users = map(lambda uid: get_user_details(uid), user_ids)
    return list(users)
"""
        available_tools = ["get_user_details"]
        
        dependencies = detect_tool_dependencies(code, "my_tool", available_tools)
        
        assert len(dependencies) == 1
        assert "get_user_details" in dependencies

    def test_empty_available_tools(self):
        """Test with empty available tools list."""
        code = """
def my_tool(user_id: str):
    '''Tool calling function'''
    user = get_user_details(user_id)
    return user
"""
        available_tools = []
        
        dependencies = detect_tool_dependencies(code, "my_tool", available_tools)
        
        assert len(dependencies) == 0

    def test_complex_real_world_example(self):
        """Test with a complex real-world example."""
        code = """
def book_reservation(
    user_id: str,
    origin: str,
    destination: str,
    flight_type: str,
    cabin: str,
    flights: str,
    passengers: str,
    payment_methods: str,
    total_baggages: int = 0,
    nonfree_baggages: int = 0,
    insurance: str = None
):
    '''Creates a flight reservation for a user with specified travel details.'''
    # Validate user exists
    user = get_user_details(user_id)
    
    # Search for flights
    if flight_type == "direct":
        available_flights = search_direct_flight(origin, destination, "2024-01-01")
    else:
        available_flights = search_onestop_flight(origin, destination, "2024-01-01")
    
    # Process payment
    payment_result = process_payment(user_id, payment_methods)
    
    # Create reservation
    reservation = create_reservation(user_id, flights, passengers)
    
    return reservation
"""
        available_tools = [
            "get_user_details",
            "search_direct_flight",
            "search_onestop_flight",
            "process_payment",
            "create_reservation",
            "unrelated_tool"
        ]
        
        dependencies = detect_tool_dependencies(code, "book_reservation", available_tools)
        
        assert len(dependencies) == 5
        assert "get_user_details" in dependencies
        assert "search_direct_flight" in dependencies
        assert "search_onestop_flight" in dependencies
        assert "process_payment" in dependencies
        assert "create_reservation" in dependencies
        assert "unrelated_tool" not in dependencies
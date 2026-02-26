"""Integration tests for dependency loading and execution."""

import pytest
from skillberry_store.modules.file_executor import FileExecutor


class TestDependencyIntegration:
    """Integration tests for tool dependency loading and execution."""

    @pytest.mark.asyncio
    async def test_execute_tool_with_dependency(self):
        """Test executing a tool that depends on another tool."""
        
        # Define the dependency tool
        dependency_code = """
def get_user_details(user_id: str):
    '''Get user details by ID'''
    return {"id": user_id, "name": "John Doe", "email": "john@example.com"}
"""
        
        # Define the main tool that uses the dependency
        main_tool_code = """
def process_user(user_id: str):
    '''Process user information'''
    user = get_user_details(user_id)
    return f"Processing user: {user['name']} ({user['email']})"
"""
        
        # Create manifest for the main tool
        manifest = {
            "name": "process_user",
            "description": "Process user information",
            "programming_language": "python",
            "packaging_format": "code"
        }
        
        # Create manifest for the dependency
        dependency_manifest = {
            "name": "get_user_details",
            "description": "Get user details",
            "programming_language": "python",
            "packaging_format": "code"
        }
        
        # Create FileExecutor with dependency
        executor = FileExecutor(
            name="process_user",
            file_content=main_tool_code,
            file_manifest=manifest,
            dependent_file_contents=[dependency_code],
            dependent_tools_as_dict=[dependency_manifest],
            execute_python_locally=True
        )
        
        # Execute the tool
        result = await executor.execute_file(parameters={"user_id": "123"})
        
        # Verify the result
        assert result is not None
        assert "Processing user: John Doe" in result["return value"]
        assert "john@example.com" in result["return value"]

    @pytest.mark.asyncio
    async def test_execute_tool_with_multiple_dependencies(self):
        """Test executing a tool with multiple dependencies."""
        
        # Define dependency 1
        dep1_code = """
def get_user_name(user_id: str):
    '''Get user name'''
    return "Alice Smith"
"""
        
        # Define dependency 2
        dep2_code = """
def get_user_email(user_id: str):
    '''Get user email'''
    return "alice@example.com"
"""
        
        # Define main tool
        main_code = """
def format_user_info(user_id: str):
    '''Format user information'''
    name = get_user_name(user_id)
    email = get_user_email(user_id)
    return f"{name} <{email}>"
"""
        
        manifest = {
            "name": "format_user_info",
            "description": "Format user info",
            "programming_language": "python",
            "packaging_format": "code"
        }
        
        dep1_manifest = {"name": "get_user_name"}
        dep2_manifest = {"name": "get_user_email"}
        
        executor = FileExecutor(
            name="format_user_info",
            file_content=main_code,
            file_manifest=manifest,
            dependent_file_contents=[dep1_code, dep2_code],
            dependent_tools_as_dict=[dep1_manifest, dep2_manifest],
            execute_python_locally=True
        )
        
        result = await executor.execute_file(parameters={"user_id": "456"})
        
        assert result is not None
        assert "Alice Smith" in result["return value"]
        assert "alice@example.com" in result["return value"]

    @pytest.mark.asyncio
    async def test_execute_tool_without_dependencies(self):
        """Test executing a tool with no dependencies."""
        
        code = """
def add_numbers(a: int, b: int):
    '''Add two numbers'''
    return a + b
"""
        
        manifest = {
            "name": "add_numbers",
            "description": "Add two numbers",
            "programming_language": "python",
            "packaging_format": "code"
        }
        
        executor = FileExecutor(
            name="add_numbers",
            file_content=code,
            file_manifest=manifest,
            dependent_file_contents=[],
            dependent_tools_as_dict=[],
            execute_python_locally=True
        )
        
        result = await executor.execute_file(parameters={"a": 5, "b": 3})
        
        assert result is not None
        assert "8" in result["return value"]

    @pytest.mark.asyncio
    async def test_missing_dependency_error(self):
        """Test that missing dependency causes an error."""
        
        # Main tool that calls a non-existent function
        code = """
def my_tool(user_id: str):
    '''Tool with missing dependency'''
    return missing_function(user_id)
"""
        
        manifest = {
            "name": "my_tool",
            "description": "Tool with missing dependency",
            "programming_language": "python",
            "packaging_format": "code"
        }
        
        executor = FileExecutor(
            name="my_tool",
            file_content=code,
            file_manifest=manifest,
            dependent_file_contents=[],  # No dependencies provided
            dependent_tools_as_dict=[],
            execute_python_locally=True
        )
        
        # Should return an error about missing function
        result = await executor.execute_file(parameters={"user_id": "123"})
        
        # Verify the result contains an error
        assert "error" in result
        # Verify the error message mentions the missing function
        assert "missing_function" in str(result["error"]) or "not defined" in str(result["error"])

    @pytest.mark.asyncio
    async def test_nested_dependency_calls(self):
        """Test tool with nested dependency calls."""
        
        # Dependency that will be called
        dep_code = """
def calculate_tax(amount: float):
    '''Calculate tax'''
    return amount * 0.1
"""
        
        # Main tool with nested call
        main_code = """
def process_payment(amount: float):
    '''Process payment with tax'''
    tax = calculate_tax(amount)
    total = amount + tax
    return f"Amount: ${amount}, Tax: ${tax}, Total: ${total}"
"""
        
        manifest = {
            "name": "process_payment",
            "description": "Process payment",
            "programming_language": "python",
            "packaging_format": "code"
        }
        
        dep_manifest = {"name": "calculate_tax"}
        
        executor = FileExecutor(
            name="process_payment",
            file_content=main_code,
            file_manifest=manifest,
            dependent_file_contents=[dep_code],
            dependent_tools_as_dict=[dep_manifest],
            execute_python_locally=True
        )
        
        result = await executor.execute_file(parameters={"amount": 100.0})
        
        assert result is not None
        assert "Amount: $100" in result["return value"]
        assert "Tax: $10" in result["return value"]
        assert "Total: $110" in result["return value"]
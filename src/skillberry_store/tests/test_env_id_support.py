"""Test env_id support in function execution."""

import pytest
from skillberry_store.modules.file_executor import FileExecutor


class TestEnvIdSupport:
    """Test that env_id is properly passed to executed functions."""

    @pytest.mark.asyncio
    async def test_execute_tool_with_env_id(self):
        """Test executing a tool that uses env_id."""
        
        # Define a tool that uses env_id
        code = """
def get_environment_info():
    '''Get environment information using env_id'''
    if env_id is not None:
        return f"Running in environment: {env_id}"
    else:
        return "No environment specified"
"""
        
        manifest = {
            "name": "get_environment_info",
            "description": "Get environment info",
            "programming_language": "python",
            "packaging_format": "code"
        }
        
        executor = FileExecutor(
            name="get_environment_info",
            file_content=code,
            file_manifest=manifest,
            dependent_file_contents=[],
            dependent_tools_as_dict=[],
            execute_python_locally=True
        )
        
        # Execute with env_id
        result = await executor.execute_file(parameters={}, env_id="test_env_123")
        
        assert result is not None
        assert "Running in environment: test_env_123" in result["return value"]

    @pytest.mark.asyncio
    async def test_execute_tool_with_dependency_using_env_id(self):
        """Test executing a tool with dependency that uses env_id."""
        
        # Define dependency that uses env_id
        dependency_code = """
def get_reservation_details(user_id: str):
    '''Get reservation details using env_id'''
    if env_id is not None:
        return {"user_id": user_id, "env": env_id, "status": "confirmed"}
    else:
        return {"user_id": user_id, "env": "unknown", "status": "pending"}
"""
        
        # Define main tool that calls the dependency
        main_code = """
def get_reservations_details(user_id: str):
    '''Get all reservation details'''
    details = get_reservation_details(user_id)
    return f"User: {details['user_id']}, Env: {details['env']}, Status: {details['status']}"
"""
        
        manifest = {
            "name": "get_reservations_details",
            "description": "Get reservations details",
            "programming_language": "python",
            "packaging_format": "code"
        }
        
        dependency_manifest = {
            "name": "get_reservation_details",
            "description": "Get reservation details",
            "programming_language": "python",
            "packaging_format": "code"
        }
        
        executor = FileExecutor(
            name="get_reservations_details",
            file_content=main_code,
            file_manifest=manifest,
            dependent_file_contents=[dependency_code],
            dependent_tools_as_dict=[dependency_manifest],
            execute_python_locally=True
        )
        
        # Execute with env_id
        result = await executor.execute_file(
            parameters={"user_id": "aarav_ahmed_6699"}, 
            env_id="production_env"
        )
        
        assert result is not None
        assert "aarav_ahmed_6699" in result["return value"]
        assert "production_env" in result["return value"]
        assert "confirmed" in result["return value"]

    @pytest.mark.asyncio
    async def test_execute_tool_without_env_id(self):
        """Test executing a tool without env_id (should still work)."""
        
        code = """
def simple_function(x: int):
    '''Simple function that doesn't use env_id'''
    return x * 2
"""
        
        manifest = {
            "name": "simple_function",
            "description": "Simple function",
            "programming_language": "python",
            "packaging_format": "code"
        }
        
        executor = FileExecutor(
            name="simple_function",
            file_content=code,
            file_manifest=manifest,
            dependent_file_contents=[],
            dependent_tools_as_dict=[],
            execute_python_locally=True
        )
        
        # Execute without env_id
        result = await executor.execute_file(parameters={"x": 5})
        
        assert result is not None
        assert "10" in result["return value"]
"""
E2E test for SDK add_tool command.
Tests the SDK's add_tool_from_python functionality against a running store service.

Prerequisites:
    The skillberry_store_sdk must be installed. To install it, run:
    
    pip install -e client/python/skillberry_store_sdk/
    
    Or from the skillberry-store root directory:
    
    cd client/python/skillberry_store_sdk && pip install -e .
"""

import os
import sys
import tempfile
import textwrap
import pytest

# Check if SDK is installed
try:
    from skillberry_store_sdk.api_client import ApiClient
    from skillberry_store_sdk.configuration import Configuration
    from skillberry_store_sdk.api.tools_api import ToolsApi
except ImportError as e:
    pytest.skip(
        f"skillberry_store_sdk is not installed. "
        f"Please install it using: pip install -e client/python/skillberry_store_sdk/\n"
        f"Error: {e}",
        allow_module_level=True
    )

from skillberry_store.tests.e2e.fixtures import run_sbs

BASE_URL = "http://localhost:8000"


@pytest.fixture
def sdk_client():
    """Create an SDK client configured for the test server."""
    config = Configuration(host=BASE_URL)
    api_client = ApiClient(configuration=config)
    return ToolsApi(api_client=api_client)


@pytest.mark.asyncio
async def test_sdk_add_tool(run_sbs, sdk_client):
    """Test SDK add_tool functionality with a simple Python file."""
    # Create a temporary Python file with a sample tool function
    # Use textwrap.dedent to remove leading indentation
    tool_content = textwrap.dedent("""
    def calculate_sum(x: int, y: int) -> int:
        '''Calculate the sum of two numbers.
        
        This function adds two integers together and returns the result.
        
        Args:
            x: The first number to add
            y: The second number to add
            
        Returns:
            The sum of x and y
        '''
        return x + y
    """).strip()
    
    # Write content to a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(tool_content)
        temp_path = f.name
    
    # Debug: Print the file content to verify
    print(f"\n=== Created temp file: {temp_path} ===")
    with open(temp_path, 'r') as f:
        content = f.read()
        print(f"File content:\n{repr(content)}")
        print(f"=== End of file content ===\n")
        print(f"Created temporary file at: {temp_path}")
    
    try:
        # Add the tool using SDK - pass the file path
        result = sdk_client.add_tool_from_python_tools_add_post(
            tool=temp_path
        )
        
        # Verify the result
        assert result is not None
        assert isinstance(result, dict)
        assert result.get("name") == "calculate_sum"
        assert "uuid" in result
        uuid_value = result.get("uuid")
        assert uuid_value is not None and len(uuid_value) == 36  # UUID4 format
        assert "module_name" in result
        module_name = result.get("module_name")
        assert module_name is not None and module_name.endswith(".py")
        
        # Verify the tool was actually created by retrieving it
        tool = sdk_client.get_tool_tools_name_get(name="calculate_sum")
        assert tool is not None
        assert tool.get("name") == "calculate_sum"
        
        # Cleanup
        sdk_client.delete_tool_tools_name_delete(name="calculate_sum")
        
    except Exception as e:
        # If test fails, try to cleanup anyway
        try:
            sdk_client.delete_tool_tools_name_delete(name="calculate_sum")
        except:
            pass
        raise e
    finally:
        # Remove temporary file
        if os.path.exists(temp_path):
            os.unlink(temp_path)

# Made with Bob

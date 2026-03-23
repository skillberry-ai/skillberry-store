"""
Pytest configuration for integration tests.

These tests require a running skillberry-store service.
The developer is responsible for starting the service before running tests.
"""

import pytest
import requests
from skillberry_store_sdk import ApiClient, Configuration
from skillberry_store_sdk.api.tools_api import ToolsApi
from skillberry_store_sdk.api.skills_api import SkillsApi
from skillberry_store_sdk.api.snippets_api import SnippetsApi


def check_service_available(host="http://localhost:8000", timeout=2):
    """
    Check if the skillberry-store service is available.
    
    Args:
        host: The service host URL
        timeout: Request timeout in seconds
        
    Returns:
        bool: True if service is available, False otherwise
    """
    try:
        response = requests.get(f"{host}/docs", timeout=timeout)
        return response.status_code == 200
    except (requests.ConnectionError, requests.Timeout):
        return False


@pytest.fixture(scope="session", autouse=True)
def check_service():
    """
    Automatically check if service is running before any integration tests.
    Skip all integration tests if service is not available.
    """
    if not check_service_available():
        pytest.skip(
            "Skillberry-store service is not running on http://localhost:8000. "
            "Please start the service before running integration tests.",
            allow_module_level=True
        )


@pytest.fixture(scope="session")
def api_config():
    """
    Create API configuration for the skillberry-store service.
    
    Assumes service is running on localhost:8000.
    Override with environment variables if needed.
    """
    config = Configuration(
        host="http://localhost:8000"
    )
    return config


@pytest.fixture(scope="session")
def api_client(api_config):
    """Create API client instance."""
    return ApiClient(configuration=api_config)


@pytest.fixture(scope="session")
def tools_api(api_client):
    """Create ToolsApi instance."""
    return ToolsApi(api_client=api_client)


@pytest.fixture(scope="session")
def skills_api(api_client):
    """Create SkillsApi instance."""
    return SkillsApi(api_client=api_client)


@pytest.fixture(scope="session")
def snippets_api(api_client):
    """Create SnippetsApi instance."""
    return SnippetsApi(api_client=api_client)


@pytest.fixture(scope="function")
def test_tool_file():
    """Provide a simple test Python file for tool creation."""
    content = b'''def add_numbers(a: int, b: int) -> int:
    """Add two numbers together.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        The sum of a and b
    """
    return a + b
'''
    return content


@pytest.fixture(scope="function")
def test_snippet_content():
    """Provide test content for snippet creation."""
    return "This is a test snippet content for integration testing."

# Made with Bob

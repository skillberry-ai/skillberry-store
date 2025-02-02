from agents.tools_service_api import execute_tool
from unittest.mock import patch, Mock
import pytest
import requests

class TestToolsServiceApi:

    @patch('agents.tools_service_api.requests.post')
    def test_execute_tool_returns_none_on_non_200_response(self, mock_post):
        """
        Test that execute_tool returns None when the response status code is not 200
        """
        # Arrange
        base_url = "http://example.com"
        tool_name = "test_tool"
        parameters = {"param1": "value1"}
        mock_response = requests.Response()
        mock_response.status_code = 404
        mock_post.return_value = mock_response

        # Act
        result = execute_tool(base_url, tool_name, parameters)

        # Assert
        assert result is None
        mock_post.assert_called_once_with(
            f"{base_url}/execute/{tool_name}{tool_name}",
            headers={"Content-Type": "application/json"},
            data=parameters
        )

    def test_execute_tool_successful_response(self):
        """
        Test execute_tool function when the API response is successful.
        """
        # Mock the requests.post method
        with patch('agents.tools_service_api.requests.post') as mock_post:
            # Set up the mock response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"result": "success"}
            mock_post.return_value = mock_response

            # Test data
            base_url = "http://example.com"
            tool_name = "test_tool"
            parameters = {"param1": "value1", "param2": "value2"}

            # Call the function
            result = execute_tool(base_url, tool_name, parameters)

            # Assert the result
            assert result == {"result": "success"}

            # Verify the API call
            expected_url = f"{base_url}/execute/{tool_name}{tool_name}"
            mock_post.assert_called_once_with(
                expected_url,
                headers={"Content-Type": "application/json"},
                data=parameters
            )

    def test_execute_tool_with_incorrect_parameter_type(self):
        """
        Test execute_tool with incorrect parameter type.
        """
        result = execute_tool("http://example.com", "tool_name", "invalid_params")
        assert result is None


    def test_execute_tool_with_large_parameters(self):
        """
        Test execute_tool with a very large parameters dictionary.
        """
        large_params = {f"param_{i}": "value" for i in range(1000)}
        result = execute_tool("http://example.com", "tool_name", large_params)
        assert result is None

    @patch('requests.post')
    def test_execute_tool_with_non_200_status_code(self, mock_post):
        """
        Test execute_tool when the response status code is not 200.
        """
        mock_response = requests.Response()
        mock_response.status_code = 404
        mock_post.return_value = mock_response
        result = execute_tool("http://example.com", "tool_name", {"param": "value"})
        assert result is None

    def test_execute_tool_with_very_long_name(self):
        """
        Test execute_tool with a very long tool name.
        """
        long_name = "a" * 1000
        result = execute_tool("http://example.com", long_name, {"param": "value"})
        assert result is None

    #def test_execute_tool_with_tools_repo(self):
    #    """
    #    Test execute_tool with tools repo.
    #    """
    #    base_url = "http://9.148.245.32:8000"
    #    tool_name = "add_two_numbers.py"
    #    result = execute_tool(base_url, tool_name, {"a": "1","b":2})
    #    assert result is "3"
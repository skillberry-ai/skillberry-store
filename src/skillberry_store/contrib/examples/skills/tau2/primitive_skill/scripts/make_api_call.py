import inspect
import requests
import os

# Define the URL
base_url = "http://127.0.0.1:8004"
tools_url = f"{base_url}/{env_id}/tools"


def _make_api_call(**kwargs):
    """Helper function to make API calls with consistent structure."""
    method_name = inspect.currentframe().f_back.f_code.co_name
    headers = {"Content-Type": "application/json"}
    url = f"{tools_url}/{method_name}"
    response = requests.post(url, json={"name": method_name, "arguments": kwargs}, headers=headers)

    if response.status_code != 200:
        raise requests.exceptions.HTTPError(f"HTTP {response.status_code}: {response.text}")

    result = response.json()
    # Tau2 environment manager stores the response as flattened json string inside "content" key.
    # However, on a failure - content key is a string containing the error message
    try:
        return json.loads(result["content"])
    except (json.JSONDecodeError, TypeError):
        return result["content"]

import pytest
from fastapi.testclient import TestClient

from mcp.client.sse import sse_client
from mcp.client.session import ClientSession
from blueberry_tools_service.fast_api.server import BTS
from blueberry_tools_service.tests.utils import clean_test_tmp_dir


def test_health_endpoint():
    """Test that the health endpoint returns the expected response."""

    clean_test_tmp_dir()
    app = BTS()
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

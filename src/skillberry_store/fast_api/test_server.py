import pytest
from fastapi.testclient import TestClient

from mcp.client.sse import sse_client
from mcp.client.session import ClientSession
from skillberry_store.fast_api.server import SBS
from skillberry_store.tests.utils import clean_test_tmp_dir


def test_health_endpoint():
    """Test that the health endpoint returns the expected response."""

    clean_test_tmp_dir()
    app = SBS()
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

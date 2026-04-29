"""
Common test fixtures for e2e tests.
"""

import asyncio
import logging
import os
import pytest
import threading

from skillberry_store.fast_api.server import SBS
from skillberry_store.tests.utils import clean_test_tmp_dir, wait_until_server_ready

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def run_sbs():
    """
    Setup and teardown fixture for the skillberry store service.

    Setup - runs the skillberry store service once for all test modules using threading.
    Teardown - cleans up resources.

    Note: Using session scope to ensure only one server instance runs,
    avoiding port conflicts (especially for Prometheus metrics on port 8090).
    This approach uses threading (like curl tests) instead of subprocess for simplicity.
    """
    logger.info("Starting SBS server in background thread")
    clean_test_tmp_dir()
    
    # Set environment to disable UI and Prometheus for tests
    os.environ["ENABLE_UI"] = "false"
    os.environ["PROMETHEUS_METRICS_PORT"] = "0"  # Disable Prometheus to avoid port conflicts
    
    # Start server in daemon thread
    def start_server():
        try:
            app = SBS()
            app.run()
        except Exception as e:
            logger.error(f"Server failed to start: {e}")
            raise
    
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Wait for server to be ready using async helper in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(wait_until_server_ready(timeout=60))
        logger.info("SBS server is ready")
    except TimeoutError:
        logger.error("Server failed to start within timeout")
        raise RuntimeError("Server failed to become ready within 60 seconds")
    finally:
        loop.close()

    yield

    logger.info("Cleaning up SBS server")
    # Daemon thread will be terminated when main process exits
    clean_test_tmp_dir()

# Made with Bob

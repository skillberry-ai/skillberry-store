"""
Common test fixtures for e2e tests.
"""

import asyncio
import logging
import os
import pytest
import threading
from io import StringIO
import queue

from skillberry_store.fast_api.server import SBS
from skillberry_store.tests.utils import clean_test_tmp_dir, wait_until_server_ready

logger = logging.getLogger(__name__)


class ThreadSafeLogCapture(logging.Handler):
    """
    Thread-safe log handler that captures logs from all threads including daemon threads.
    Uses a queue to safely transfer log records between threads.
    """
    
    def __init__(self):
        super().__init__()
        self.log_queue = queue.Queue()
        self.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(threadName)s] - %(message)s'
        )
        self.setFormatter(formatter)
    
    def emit(self, record):
        """Called by logging system to emit a log record."""
        try:
            msg = self.format(record)
            self.log_queue.put(msg)
        except Exception:
            self.handleError(record)
    
    def get_logs(self):
        """Get all captured logs as a string."""
        logs = []
        while not self.log_queue.empty():
            try:
                logs.append(self.log_queue.get_nowait())
            except queue.Empty:
                break
        return '\n'.join(logs)
    
    def clear(self):
        """Clear all captured logs."""
        while not self.log_queue.empty():
            try:
                self.log_queue.get_nowait()
            except queue.Empty:
                break


# Global log capture handler for the session
_session_log_handler = None


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
    global _session_log_handler
    
    logger.info("Starting SBS server in background thread")
    clean_test_tmp_dir()
    
    # Set environment to disable UI and Prometheus for tests
    os.environ["ENABLE_UI"] = "false"
    os.environ["PROMETHEUS_METRICS_PORT"] = "0"  # Disable Prometheus to avoid port conflicts
    
    # Install session-wide log capture handler BEFORE starting server
    _session_log_handler = ThreadSafeLogCapture()
    root_logger = logging.getLogger()
    root_logger.addHandler(_session_log_handler)
    root_logger.setLevel(logging.DEBUG)
    
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
    # Remove the log handler
    if _session_log_handler:
        root_logger.removeHandler(_session_log_handler)
    # Daemon thread will be terminated when main process exits
    clean_test_tmp_dir()


@pytest.fixture(scope="function")
def capture_server_logs(request):
    """
    Capture all server logs during test execution.
    
    This fixture captures logs from the server (running in daemon thread) and makes them
    available to each test. Logs are automatically attached to the test report.
    
    Usage in tests:
        def test_something(run_sbs, capture_server_logs):
            # Your test code here
            # All server logs during this test are captured
            
            # Optionally access logs during test:
            logs = capture_server_logs.get_logs()
            assert "expected message" in logs
    
    Note: This requires the run_sbs fixture to be active (session scope).
    """
    global _session_log_handler
    
    if _session_log_handler is None:
        pytest.fail("capture_server_logs requires run_sbs fixture to be active")
    
    # Clear any logs from previous tests
    _session_log_handler.clear()
    
    # Yield a simple object with get_logs method
    class LogAccessor:
        def get_logs(self):
            if _session_log_handler is not None:
                return _session_log_handler.get_logs()
            return ""
    
    accessor = LogAccessor()
    yield accessor
    
    # Capture final logs after test completes
    captured_logs = _session_log_handler.get_logs()
    
    # Attach logs to test report (visible in pytest output)
    if captured_logs:
        request.node.add_report_section("call", "server_logs", captured_logs)
        
        # Also log to pytest output for verbose mode
        if request.config.getoption("verbose") > 0:
            logger.info(f"\n{'='*80}\nServer logs for {request.node.nodeid}:\n{captured_logs}\n{'='*80}")


# Made with Bob

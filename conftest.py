"""Root conftest.py for pytest configuration.

Shared session fixtures live here so any test tree (src/, plugins/, …) can
depend on them without redefining the SBS server in its own conftest.
"""
import asyncio
import logging
import os
import queue
import threading
from io import StringIO

import pytest


def pytest_configure(config):
    """Configure pytest based on environment variables."""
    if os.getenv("SBS_TEST_DEBUG", "").lower() == "true":
        config.option.log_cli = True
        config.option.log_cli_level = "DEBUG"
    else:
        config.option.log_cli = False


logger = logging.getLogger(__name__)


class ThreadSafeLogCapture(logging.Handler):
    """Thread-safe log handler that captures logs from all threads via a queue."""

    def __init__(self):
        super().__init__()
        self.log_queue = queue.Queue()
        self.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(threadName)s] - %(message)s'
        )
        self.setFormatter(formatter)

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_queue.put(msg)
        except Exception:
            self.handleError(record)

    def get_logs(self):
        logs = []
        while not self.log_queue.empty():
            try:
                logs.append(self.log_queue.get_nowait())
            except queue.Empty:
                break
        return '\n'.join(logs)

    def clear(self):
        while not self.log_queue.empty():
            try:
                self.log_queue.get_nowait()
            except queue.Empty:
                break


_session_log_handler = None


@pytest.fixture(scope="session")
def run_sbs():
    """Start the SBS server once per session in a daemon thread."""
    from skillberry_store.fast_api.server import SBS
    from skillberry_store.tests.utils import clean_test_tmp_dir, wait_until_server_ready

    global _session_log_handler

    logger.info("Starting SBS server in background thread")
    clean_test_tmp_dir()

    os.environ["ENABLE_UI"] = "false"
    os.environ["PROMETHEUS_METRICS_PORT"] = "0"

    _session_log_handler = ThreadSafeLogCapture()
    root_logger = logging.getLogger()
    root_logger.addHandler(_session_log_handler)
    root_logger.setLevel(logging.DEBUG)

    def start_server():
        try:
            SBS().run()
        except Exception as e:
            logger.error(f"Server failed to start: {e}")
            raise

    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

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
    if _session_log_handler:
        root_logger.removeHandler(_session_log_handler)
    clean_test_tmp_dir()


@pytest.fixture(scope="function")
def capture_server_logs(request):
    """Capture all server logs during a single test."""
    global _session_log_handler

    if _session_log_handler is None:
        pytest.fail("capture_server_logs requires run_sbs fixture to be active")

    _session_log_handler.clear()

    class LogAccessor:
        def get_logs(self):
            if _session_log_handler is not None:
                return _session_log_handler.get_logs()
            return ""

    accessor = LogAccessor()
    yield accessor

    captured_logs = _session_log_handler.get_logs()
    if captured_logs:
        request.node.add_report_section("call", "server_logs", captured_logs)
        if request.config.getoption("verbose") > 0:
            logger.info(f"\n{'='*80}\nServer logs for {request.node.nodeid}:\n{captured_logs}\n{'='*80}")


@pytest.fixture(scope="session", autouse=True)
def configure_httpx_defaults():
    """Apply a 120s default timeout to all httpx.AsyncClient instances."""
    import httpx

    original_init = httpx.AsyncClient.__init__

    def patched_init(self, *args, **kwargs):
        if 'timeout' not in kwargs:
            kwargs['timeout'] = httpx.Timeout(120.0, connect=10.0)
        original_init(self, *args, **kwargs)

    httpx.AsyncClient.__init__ = patched_init
    logger.info("Applied httpx default timeout: 120s")

    yield

    httpx.AsyncClient.__init__ = original_init
    logger.info("Restored original httpx AsyncClient.__init__")

# Made with Bob

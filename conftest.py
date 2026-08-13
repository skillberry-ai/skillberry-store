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


# Model consumed by ``skillberry_store.vdbs.vector_db_interface`` for the
# semantic encoder. Must match the string passed to ``SentenceTransformer(...)``
# in that module — if it changes there, change it here too.
_SEMANTIC_ENCODER_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@pytest.fixture(scope="session")
def ensure_semantic_encoder_cached():
    """Idempotently guarantee the sentence-transformer model is on disk.

    Motivation: ``SBS.run()`` warms the semantic encoder in the background
    at startup. On a cold ``~/.cache/huggingface`` (fresh CI runner, new
    container) that warmup downloads ~88MB from HuggingFace before
    ``/health/ready`` can return 200 — which routinely exceeds the 60s
    fixture timeout in ``run_sbs`` and errors out every e2e test in the
    session at setup. Doing the download *here*, before the server thread
    starts, moves that cost outside the readiness-wait window.

    Idempotent by construction:

      * First try to load with ``local_files_only=True``. If the cache
        already has every file the model needs (config, tokenizer, weights,
        pooling module, …), this succeeds without any network call. Cache
        hit: no-op, ~fraction of a second.
      * If any file is missing, ``local_files_only`` raises. Fall back to
        an online load, which downloads the missing pieces once. Subsequent
        test sessions on the same runner take the cache-hit path.

    Fixture is session-scoped and ``autouse=False`` — pulled in by
    ``run_sbs`` so unit / integration tests that never spawn SBS pay
    nothing. Failure to prepare the model (e.g. no cache AND no network)
    still surfaces as an ``OSError`` here rather than as a mysterious
    60s timeout deeper in the fixture chain — a much easier failure to
    diagnose in CI logs.
    """
    from sentence_transformers import SentenceTransformer

    try:
        SentenceTransformer(_SEMANTIC_ENCODER_MODEL, local_files_only=True)
        logger.info(
            "Semantic encoder model already cached (%s) — skipping download",
            _SEMANTIC_ENCODER_MODEL,
        )
        return
    except Exception as e:  # noqa: BLE001 — huggingface_hub raises several types
        logger.info(
            "Semantic encoder model not cached (%s): %s — downloading",
            _SEMANTIC_ENCODER_MODEL,
            e.__class__.__name__,
        )

    SentenceTransformer(_SEMANTIC_ENCODER_MODEL)
    logger.info(
        "Semantic encoder model downloaded and cached (%s)",
        _SEMANTIC_ENCODER_MODEL,
    )


@pytest.fixture(scope="session")
def run_sbs(ensure_semantic_encoder_cached, tmp_path_factory):
    """Start the SBS server once per session in a daemon thread."""
    from skillberry_store.fast_api.server import SBS
    from skillberry_store.tests.utils import clean_test_tmp_dir, wait_until_server_ready

    global _session_log_handler

    logger.info("Starting SBS server in background thread")
    clean_test_tmp_dir()

    os.environ["ENABLE_UI"] = "false"
    os.environ["PROMETHEUS_METRICS_PORT"] = "0"
    os.environ["SKILLBERRY_PLUGIN_CONFIG"] = str(
        tmp_path_factory.mktemp("plugin-config") / "plugins.json"
    )

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
def isolate_access_control_config(tmp_path_factory):
    """Prevent tests from consuming the operator's access_control_config.yaml.

    Without this shield the loader falls back to
    ``./access_control_config.yaml`` (repo root), which is a user-managed
    file. If an operator flips it to ``mode: standalone`` locally, every
    e2e/integration test that constructs ``SBS()`` would silently install
    the RBAC middleware and start returning 401 to unauthenticated
    requests. Point the env var at a non-existent path so the loader
    returns its built-in ``mode: disabled`` defaults for all tests that
    do not explicitly override it via monkeypatch.
    """
    from skillberry_store.access_control import config as acl_config

    sentinel = tmp_path_factory.mktemp("acl") / "does-not-exist.yaml"
    os.environ["SBS_ACCESS_CONTROL_CONFIG"] = str(sentinel)
    acl_config.reset_config_cache()
    yield
    os.environ.pop("SBS_ACCESS_CONTROL_CONFIG", None)
    acl_config.reset_config_cache()


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

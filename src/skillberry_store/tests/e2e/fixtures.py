"""
Common test fixtures for e2e tests.
"""

import asyncio
import os
import pytest_asyncio

from skillberry_store.tests.utils import clean_test_tmp_dir, wait_until_server_ready


@pytest_asyncio.fixture(scope="session")
async def run_sbs(request):
    """
    Setup and teardown fixture for the skillberry store service.

    Setup - runs the skillberry store service once for all test modules.
    Teardown - terminates the service and removes its resources.
    
    Note: Using session scope to ensure only one server instance runs,
    avoiding port conflicts (especially for Prometheus metrics on port 8090).
    """
    print("setup called")
    clean_test_tmp_dir()
    
    # Get the project root directory (parent of tests/e2e)
    current_file = os.path.abspath(__file__)
    e2e_dir = os.path.dirname(current_file)
    tests_dir = os.path.dirname(e2e_dir)
    project_root = os.path.dirname(tests_dir)
    
    # Set environment to disable UI and Prometheus for tests
    env = os.environ.copy()
    env["ENABLE_UI"] = "false"
    env["PROMETHEUS_METRICS_PORT"] = "0"  # Disable Prometheus to avoid port conflicts
    
    main_proc = await asyncio.create_subprocess_exec(
        "python", "-m", "skillberry_store.main",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=project_root,
        env=env,
        limit=1024 * 1024  # Increase buffer size to 1MB to prevent blocking
    )
    
    # Create background tasks to stream server output to console
    # Use a separate thread with its own event loop to avoid conflicts
    import threading
    import sys
    
    def run_stream_reader(stream, prefix, loop):
        """Run async stream reader in a separate thread with its own event loop."""
        asyncio.set_event_loop(loop)
        
        async def stream_output():
            try:
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    try:
                        decoded = line.decode().rstrip()
                        print(f"{prefix}: {decoded}", flush=True)
                        sys.stdout.flush()
                        sys.stderr.flush()
                    except Exception as decode_err:
                        print(f"{prefix}: [decode error: {decode_err}]", flush=True)
                        sys.stdout.flush()
            except Exception as e:
                print(f"{prefix} stream error: {e}", flush=True)
                sys.stdout.flush()
        
        loop.run_until_complete(stream_output())
    
    # Create separate event loops for each stream reader
    stdout_loop = asyncio.new_event_loop()
    stderr_loop = asyncio.new_event_loop()
    
    stdout_thread = threading.Thread(
        target=run_stream_reader,
        args=(main_proc.stdout, "SERVER", stdout_loop),
        daemon=True
    )
    stderr_thread = threading.Thread(
        target=run_stream_reader,
        args=(main_proc.stderr, "SERVER-ERR", stderr_loop),
        daemon=True
    )
    
    stdout_thread.start()
    stderr_thread.start()
    
    # Store thread references
    streaming_threads = [stdout_thread, stderr_thread]
    streaming_loops = [stdout_loop, stderr_loop]
    
    # Give streaming threads a moment to start
    await asyncio.sleep(0.1)
    
    # Give the server a moment to start before checking
    await asyncio.sleep(2)
    
    # Check if process is still running
    if main_proc.returncode is not None:
        print(f"Server failed to start!")
        raise RuntimeError("Server process terminated unexpectedly")
    
    await wait_until_server_ready(timeout=60)

    yield

    print("teardown called")
    # Cleanup: kill server process
    main_proc.kill()
    
    # Stop event loops in threads
    for loop in streaming_loops:
        loop.call_soon_threadsafe(loop.stop)
    
    # Wait for threads to finish (with timeout)
    for thread in streaming_threads:
        thread.join(timeout=1.0)

    clean_test_tmp_dir()
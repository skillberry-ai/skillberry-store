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
    )
    
    # Give the server a moment to start before checking
    await asyncio.sleep(2)
    
    # Check if process is still running
    if main_proc.returncode is not None:
        stdout_data = await main_proc.stdout.read() if main_proc.stdout else b""
        stderr_data = await main_proc.stderr.read() if main_proc.stderr else b""
        print(f"Server failed to start!")
        print(f"STDOUT: {stdout_data.decode()}")
        print(f"STDERR: {stderr_data.decode()}")
        raise RuntimeError("Server process terminated unexpectedly")
    
    await wait_until_server_ready(timeout=60)

    yield

    print("teardown called")
    # Cleanup: kill server process
    main_proc.kill()

    # Read to avoid transport issues
    if main_proc.stdout:
        await main_proc.stdout.read()
    if main_proc.stderr:
        await main_proc.stderr.read()

    clean_test_tmp_dir()

# Made with Bob

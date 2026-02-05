"""
Common test fixtures for e2e tests.
"""

import asyncio
import os
import pytest_asyncio

from skillberry_store.tests.utils import clean_test_tmp_dir, wait_until_server_ready


@pytest_asyncio.fixture(scope="module")
async def run_sbs(request):
    """
    Setup and teardown fixture for the skillberry store service.

    Setup - runs the skillberry store service.
    Teardown - terminates the service and removes its resources.
    """
    print("setup called")
    clean_test_tmp_dir()
    
    # Get the project root directory (parent of tests/e2e)
    current_file = os.path.abspath(__file__)
    e2e_dir = os.path.dirname(current_file)
    tests_dir = os.path.dirname(e2e_dir)
    project_root = os.path.dirname(tests_dir)
    
    main_proc = await asyncio.create_subprocess_exec(
        "python", "-m", "skillberry_store.main",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=project_root,
    )
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
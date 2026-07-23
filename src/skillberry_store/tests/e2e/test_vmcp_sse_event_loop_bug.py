"""
E2E test to reproduce the RuntimeError: event loop binding bug in VMCP SSE connections.

This test reproduces the bug found in skillberry-store.log where multiple VMCP servers
created in sequence cause RuntimeError when clients connect via SSE due to the
sse_starlette AppStatus.should_exit_event being bound to the first event loop.

Bug Pattern (from log analysis):
1. Create first VMCP server (runs in thread with event loop A) - port 10000
2. Create second VMCP server (runs in thread with event loop B) - port 10001
3. Client connects to first server via SSE (GET /sse) - works fine
4. Client connects to second server via SSE (GET /sse) - RuntimeError occurs

Root Cause:
The sse_starlette.sse.AppStatus.should_exit_event is a singleton that gets bound to
the first event loop created. When subsequent VMCP servers (in different threads with
different event loops) try to use it, asyncio raises:
  RuntimeError: <asyncio.locks.Event object> is bound to a different event loop

Location in Code:
- src/skillberry_store/modules/vmcp_server.py lines 584-591 attempts to fix this
- The fix tries to reset AppStatus.should_exit_event = None but it's not effective

Expected Behavior:
Each VMCP server should be able to handle SSE connections independently without
interfering with other servers' event loops.
"""

import asyncio
import pytest
import uuid
from mcp import ClientSession
from mcp.client.sse import sse_client

# Check if SDK is installed
try:
    from skillberry_store_sdk import ApiClient, Configuration, VmcpServersApi, SkillsApi
except ImportError as e:
    pytest.skip(
        f"skillberry_store_sdk is not installed. "
        f"Please install it using: pip install -e client/python/skillberry_store_sdk/\n"
        f"Error: {e}",
        allow_module_level=True
    )


BASE_URL = "http://localhost:8000"


@pytest.fixture
def vmcp_sdk_client():
    """Create an SDK client for VMCP servers."""
    config = Configuration(host=BASE_URL)
    api_client = ApiClient(configuration=config)
    return VmcpServersApi(api_client=api_client)


@pytest.fixture
def skills_sdk_client():
    """Create an SDK client for skills."""
    config = Configuration(host=BASE_URL)
    api_client = ApiClient(configuration=config)
    return SkillsApi(api_client=api_client)


@pytest.mark.asyncio
async def test_multiple_vmcp_servers_sse_connections_sdk(
    run_sbs, capture_server_logs, vmcp_sdk_client, skills_sdk_client
):
    """
    Test that reproduces the event loop binding bug when connecting to multiple VMCP servers via SSE.
    
    This test uses the SDK to:
    1. Create a skill with no tools (to keep it simple)
    2. Create two VMCP servers pointing to that skill (each in its own thread with its own event loop)
    3. Attempt to connect to both via SSE using MCP client
    4. The second connection should trigger RuntimeError (reproducing the bug)
    
    Once the bug is fixed, this test should pass without exceptions.
    """
    # Create a simple skill first
    skill_uuid = str(uuid.uuid4())
    skill_name = f"test_skill_for_sse_bug_{skill_uuid[:8]}"
    
    try:
        # Create skill using SDK
        skill_result = skills_sdk_client.create_skill(
            name=skill_name,
            description="Test skill for SSE bug reproduction",
            uuid=skill_uuid,
            tool_uuids=[],  # No tools needed for this test
            snippet_uuids=[]
        )
        print(f"Created skill: {skill_result.get('name')} with UUID: {skill_result.get('uuid')}")
        
        # Create two VMCP servers using SDK
        server1_uuid = str(uuid.uuid4())
        server2_uuid = str(uuid.uuid4())
        
        vmcp_servers = []
        
        # Create first VMCP server
        print(f"\nCreating first VMCP server...")
        server1_result = vmcp_sdk_client.create_vmcp_server(
            name=f"sse_test_server_1_{server1_uuid[:8]}",
            description="First VMCP server for SSE testing",
            port=10100,
            skill_uuid=skill_uuid,
            uuid=server1_uuid
        )
        vmcp_servers.append(server1_result)
        print(f"Created server 1: {server1_result.get('name')} on port {server1_result.get('port')}")
        
        # Wait for server to initialize
        await asyncio.sleep(2)
        
        # Create second VMCP server
        print(f"\nCreating second VMCP server...")
        server2_result = vmcp_sdk_client.create_vmcp_server(
            name=f"sse_test_server_2_{server2_uuid[:8]}",
            description="Second VMCP server for SSE testing",
            port=10101,
            skill_uuid=skill_uuid,
            uuid=server2_uuid
        )
        vmcp_servers.append(server2_result)
        print(f"Created server 2: {server2_result.get('name')} on port {server2_result.get('port')}")
        
        # Wait for server to initialize
        await asyncio.sleep(2)
        
        # Now attempt to connect to both servers via SSE
        # The bug manifests when the second server's SSE endpoint is accessed
        
        exceptions_caught = []
        
        # Connect to first server
        print(f"\nConnecting to first server via SSE...")
        try:
            server1_url = f"http://127.0.0.1:{server1_result.get('port')}/sse"
            # Use asyncio.wait_for to add timeout
            async with asyncio.timeout(10):  # 10 second timeout
                async with sse_client(server1_url) as (read, write):
                    async with ClientSession(read, write) as session:
                        # Initialize the session
                        await session.initialize()
                        # List tools to verify connection works
                        tools = await session.list_tools()
                        print(f"✓ Server 1 connection successful, tools: {len(tools.tools)}")
        except asyncio.TimeoutError:
            exceptions_caught.append(("server1", "Connection timed out after 10 seconds", "TimeoutError"))
            print(f"✗ Server 1 SSE connection timed out")
        except Exception as e:
            exceptions_caught.append(("server1", str(e), type(e).__name__))
            print(f"✗ Server 1 SSE connection failed: {type(e).__name__}: {e}")
        
        # Small delay between connections
        await asyncio.sleep(0.5)
        
        # Connect to second server - this is where the bug typically manifests
        print(f"\nConnecting to second server via SSE...")
        try:
            server2_url = f"http://127.0.0.1:{server2_result.get('port')}/sse"
            # Use asyncio.wait_for to add timeout - this will prevent hanging
            async with asyncio.timeout(10):  # 10 second timeout
                async with sse_client(server2_url) as (read, write):
                    async with ClientSession(read, write) as session:
                        # Initialize the session
                        await session.initialize()
                        # List tools to verify connection works
                        tools = await session.list_tools()
                        print(f"✓ Server 2 connection successful, tools: {len(tools.tools)}")
        except asyncio.TimeoutError:
            exceptions_caught.append(("server2", "Connection timed out after 10 seconds - likely due to event loop bug", "TimeoutError"))
            print(f"✗ Server 2 SSE connection timed out (this indicates the bug)")
        except Exception as e:
            exceptions_caught.append(("server2", str(e), type(e).__name__))
            print(f"✗ Server 2 SSE connection failed: {type(e).__name__}: {e}")
        
        # Look for the specific event-loop binding error in server logs.
        # capture_server_logs is wired to a session-scoped root-logger handler,
        # so a broad "RuntimeError" substring match catches unrelated tracebacks
        # from other session-scoped plugins (e.g. mock-driven dedupe/evaluator
        # handlers triggered when this test creates a skill). Match the exact
        # phrase from the bug instead.
        logs = capture_server_logs.get_logs()
        has_event_loop_error = "bound to a different event loop" in logs

        # Check if server 2 timed out (primary indicator of the bug)
        server2_timed_out = any(
            server == "server2" and error_type == "TimeoutError"
            for server, error, error_type in exceptions_caught
        )

        # Report findings
        print(f"\n{'='*80}")
        print(f"Test Results:")
        print(f"  Exceptions caught during connections: {len(exceptions_caught)}")
        for server, error, error_type in exceptions_caught:
            print(f"    {server}: {error_type}")
            print(f"      {error[:200]}")
        print(f"  Server 2 timed out: {server2_timed_out}")
        print(f"  Event loop error in logs: {has_event_loop_error}")
        print(f"{'='*80}\n")

        # The test documents the bug - it will fail until the bug is fixed
        # The bug manifests as a timeout on the second server's SSE connection
        if server2_timed_out or has_event_loop_error:
            pytest.fail(
                "BUG REPRODUCED: Second VMCP server's SSE connection timed out due to event loop bug. "
                "The server-side RuntimeError 'bound to a different event loop' prevents proper SSE stream setup. "
                "See src/skillberry_store/modules/vmcp_server.py "
                "_patch_sse_starlette_for_multi_loop for the fix."
            )
        
    finally:
        # Cleanup: delete VMCP servers and skill
        print(f"\nCleaning up...")
        try:
            vmcp_sdk_client.delete_vmcp_server(
                uuid_or_name=server1_uuid
            )
            print(f"Deleted server 1")
        except Exception as e:
            print(f"Failed to delete server 1: {e}")
        
        try:
            vmcp_sdk_client.delete_vmcp_server(
                uuid_or_name=server2_uuid
            )
            print(f"Deleted server 2")
        except Exception as e:
            print(f"Failed to delete server 2: {e}")
        
        try:
            skills_sdk_client.delete_skill(
                uuid_or_name=skill_uuid
            )
            print(f"Deleted skill")
        except Exception as e:
            print(f"Failed to delete skill: {e}")


@pytest.mark.asyncio
async def test_sequential_vmcp_server_creation_sdk(
    run_sbs, capture_server_logs, vmcp_sdk_client, skills_sdk_client
):
    """
    Test that creates VMCP servers sequentially and verifies the bug pattern.
    
    This is a simpler version that creates multiple servers and checks if the
    event loop error appears in logs, without attempting MCP client connections.
    """
    # Create a skill
    skill_uuid = str(uuid.uuid4())
    skill_name = f"sequential_test_skill_{skill_uuid[:8]}"
    
    try:
        skill_result = skills_sdk_client.create_skill(
            name=skill_name,
            description="Test skill for sequential server creation",
            uuid=skill_uuid,
            tool_uuids=[],
            snippet_uuids=[]
        )
        print(f"Created skill: {skill_result.get('name')}")
        
        # Create 3 VMCP servers sequentially
        num_servers = 3
        server_uuids = []
        
        for i in range(num_servers):
            server_uuid = str(uuid.uuid4())
            server_uuids.append(server_uuid)
            
            print(f"\nCreating VMCP server {i+1}/{num_servers}...")
            result = vmcp_sdk_client.create_vmcp_server(
                name=f"sequential_server_{i}_{server_uuid[:8]}",
                description=f"Sequential test server {i}",
                port=10200 + i,
                skill_uuid=skill_uuid,
                uuid=server_uuid
            )
            print(f"Created: {result.get('name')} on port {result.get('port')}")
            
            # Wait for server to initialize
            await asyncio.sleep(1.5)
        
        # Check logs for the bug
        logs = capture_server_logs.get_logs()
        has_event_loop_error = "bound to a different event loop" in logs
        
        print(f"\n{'='*80}")
        print(f"Sequential Creation Test Results:")
        print(f"  Servers created: {num_servers}")
        print(f"  Event loop error in logs: {has_event_loop_error}")
        print(f"{'='*80}\n")
        
        # Note: The bug might not manifest just from creation, but from SSE connections
        # This test documents the setup that leads to the bug
        
    finally:
        # Cleanup
        print(f"\nCleaning up...")
        for server_uuid in server_uuids:
            try:
                vmcp_sdk_client.delete_vmcp_server(
                    uuid_or_name=server_uuid
                )
            except Exception as e:
                print(f"Failed to delete server {server_uuid}: {e}")
        
        try:
            skills_sdk_client.delete_skill(
                uuid_or_name=skill_uuid
            )
        except Exception as e:
            print(f"Failed to delete skill: {e}")

# Made with Bob

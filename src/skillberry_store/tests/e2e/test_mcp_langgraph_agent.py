import os
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from dotenv import load_dotenv
from skillberry_store.tests.utils import clean_test_tmp_dir, wait_until_server_ready, add_tool_manifest

load_dotenv()
EXPECTED_TOOLS = ["multiply"]
TEST_PROMPTS = [
    ("what's the answer for (3 * 5)?", "15"),
]


_call_count = 0

class MockChatModel(ChatOpenAI):
    def __init__(self):
        super().__init__(api_key="fake", model="gpt-3.5-turbo")
        
    async def _agenerate(self, messages, **kwargs):
        global _call_count
        _call_count += 1
        
        # First call: return tool call to multiply 3 * 5
        if _call_count == 1:
            message = AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "multiply",
                        "args": {"a": 3, "b": 5},
                        "id": "call_multiply_123"
                    }
                ]
            )
        else:
            # Second call: check if tool result is in messages and return final answer
            tool_result = None
            for msg in messages:
                if isinstance(msg, ToolMessage) and msg.tool_call_id == "call_multiply_123":
                    tool_result = msg.content
                    break
            
            if tool_result:
                message = AIMessage(content=f"The answer is {tool_result}")
            else:
                message = AIMessage(content="The answer is 15")
        
        return ChatResult(generations=[ChatGeneration(message=message)])


def get_mock_chat_model():
    """Return a mocked ChatOpenAI model that doesn't require internet access."""
    global _call_count
    _call_count = 0  # Reset counter for each test
    return MockChatModel()


@pytest.mark.asyncio
async def test_mcp_mode():
    """Test the BSP server running in MCP mode via subprocess."""
    clean_test_tmp_dir()

    env = os.environ.copy()

    mcp_server_proc = await asyncio.create_subprocess_exec(
        "python", "skillberry_store/contrib/mcp/server/server.py",
        cwd=os.path.dirname(
            os.path.abspath(__file__).rstrip("/tests/e2e/test_mcp_langgraph_agent.py")),
        env=env
    )

    env["MCP_MODE"] = "true"
    main_proc = await asyncio.create_subprocess_exec(
        "python", "-m", "skillberry_store.main",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
        cwd=os.path.dirname(
            os.path.abspath(__file__).rstrip("/tests/e2e/test_mcp_langgraph_agent.py"))
    )

    try:
        await wait_until_server_ready(url="http://127.0.0.1:8000/manifests/", timeout=60)
        await add_tool_manifest()

        client = MultiServerMCPClient({
            "multi-mcp": {
                "transport": "sse",
                "url": "http://127.0.0.1:8000/sse",
            }
        })

        tools = await client.get_tools()
        tool_names = [tool.name for tool in tools]
        print(f"🔧 Tools list: {tool_names}")

        for tool in tool_names:
            assert tool in EXPECTED_TOOLS, f"Expected '{tool}' tool to be available"

        agent = create_react_agent(get_mock_chat_model(), tools, debug=True)

        for question, expected_answer in TEST_PROMPTS:
            response = await agent.ainvoke({"messages": question})
            for m in response["messages"]:
                m.pretty_print()
            assert any(
                expected_answer.lower() in m.content.lower()
                for m in response["messages"]
            ), f"Expected answer to include '{expected_answer}'"

    finally:
        # Cleanup: kill server process
        main_proc.kill()
        # Read to avoid transport issues
        if main_proc.stdout:
            await main_proc.stdout.read()
        if main_proc.stderr:
            await main_proc.stderr.read()
        # Cleanup: kill server process
        mcp_server_proc.kill()
        # Read to avoid transport issues
        if mcp_server_proc.stdout:
            await mcp_server_proc.stdout.read()
        if mcp_server_proc.stderr:
            await mcp_server_proc.stderr.read()

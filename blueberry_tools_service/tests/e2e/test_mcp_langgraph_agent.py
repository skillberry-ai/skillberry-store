import os
import asyncio
import pytest
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from blueberry_tools_service.tests.utils import clean_test_tmp_dir, wait_until_server_ready, add_tool_manifest

load_dotenv()
EXPECTED_TOOLS = ["multiply"]
TEST_PROMPTS = [
    ("what's the answer for (3 * 5)?", "15"),
]


def get_chat_model() -> ChatOpenAI:
    """Initialize and return a ChatOpenAI model from environment settings."""
    rits_api_key = os.environ.get("RITS_API_KEY")
    if not rits_api_key:
        raise ValueError("RITS_API_KEY environment variable is not set.")

    return ChatOpenAI(
        model=os.environ.get("MODEL_NAME",
                             "rits/meta-llama/llama-3-3-70b-instruct"),
        base_url=os.environ.get("BASE_MODEL_URL",
                                "http://blueberry.sl.cloud9.ibm.com:4000/"),  # using blueberry proxy IP as default
        api_key=rits_api_key,
        temperature=0.7,
    )


@pytest.mark.asyncio
async def test_mcp_mode():
    """Test the BSP server running in MCP mode via subprocess."""
    clean_test_tmp_dir()

    env = os.environ.copy()

    mcp_server_proc = await asyncio.create_subprocess_exec(
        "python", "blueberry_tools_service/contrib/mcp/server/server.py",
        cwd=os.path.dirname(
            os.path.abspath(__file__).rstrip("/tests/e2e/test_mcp_langgraph_agent.py")),
        env=env
    )

    env["MCP_MODE"] = "true"
    main_proc = await asyncio.create_subprocess_exec(
        "python", "-m", "blueberry_tools_service.main",
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

        agent = create_react_agent(get_chat_model(), tools, debug=True)

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

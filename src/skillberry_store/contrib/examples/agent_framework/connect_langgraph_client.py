import os
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize the chat model using OpenAI-compatible settings.
model = ChatOpenAI(
    model=os.environ.get("MODEL_NAME"),
    base_url=os.environ["BASE_URL"],
    api_key=os.environ["OPENAI_API_KEY"],
    temperature=0.7,
)

async def main():
    """
    The main asynchronous function that connects to the SBS server and creates a reactive LangGraph agent.

    Returns:
        None
    """
    # Create and connect a MultiServerMCPClient to the SBS server
    async with MultiServerMCPClient() as client:
        await client.connect_to_server(
            "multi-mcp",
            transport="sse",
            url="http://127.0.0.1:8000/sse",
        )

        # Retrieve the tools exposed by the connected MCP server(s)
        tools = client.get_tools()
        print(f"🔧 Tools list:{[tool.name for tool in tools]}")

        # Create a reactive LangGraph agent using the MCP tools
        agent = create_react_agent(model, tools)

        # Use calculator tool
        response = await agent.ainvoke({"messages": "what's the answer for (10 + 5)?"})
        for m in response["messages"]:
            m.pretty_print()

if __name__ == "__main__":
    asyncio.run(main())

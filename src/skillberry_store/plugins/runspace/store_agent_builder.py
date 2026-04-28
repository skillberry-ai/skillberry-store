"""Store Agent builder: builds a RunspaceAgent request for the Store Agent.

The Store Agent is an AI assistant that manages the Skillberry Store via MCP tools.
It can create tools, skills, snippets, and VMCP servers on behalf of the user.
"""

import logging
import os
import tempfile
from typing import Any, Dict

from .agentic_exporter import build_default_env

logger = logging.getLogger(__name__)

STORE_AGENT_PROMPT = """\
You are the Skillberry Store Assistant. You have access to the Skillberry Store \
via MCP tools. Use the skillberry-store MCP tools to fulfill the user's request.

## Available MCP Tools

You have these tools from the "skillberry-store" MCP server:
- list_tools — List all tools (name, description, state)
- get_tool_metadata — Get full tool manifest
- get_tool_code — Get tool Python source code
- update_tool_code — Update tool source code
- update_tool_metadata — Update description, tags, state, version
- create_tool — Create a new tool from Python code
- execute_tool — Execute a tool with parameters
- search_tools — Semantic search over tool descriptions
- list_skills — List all skills
- get_skill — Get skill with resolved tools
- create_skill — Create a new skill with tool names
- add_tool_to_skill — Add a tool to a skill
- remove_tool_from_skill — Remove a tool from a skill
- create_vmcp_server — Create and start a VMCP server for a skill

## User Request

{user_request}

## Context Files

The user may have uploaded context files. If so, they are available in your \
context directory. Read them to understand requirements, specs, or code samples \
the user provided.

## Guidelines

1. Use the MCP tools to fulfill the request. Do NOT try to write files directly.
2. When creating tools, write clean Python code with docstrings and proper error handling.
3. When creating a VMCP server, include the `claude mcp add` command in your response \
   so the user knows how to connect to it.
4. If you create multiple tools, consider grouping them into a skill.
5. Verify your work — after creating tools, try to list them to confirm they exist.
"""


def build_store_agent_request(
    user_prompt: str,
    agent_mcp_port: int = 9999,
) -> Dict[str, Any]:
    """Build a RunspaceAgent request for the Store Agent."""
    base_dir = tempfile.mkdtemp(prefix="sbs_store_agent_")
    editable_dir = os.path.join(base_dir, "editable")
    context_dir = os.path.join(base_dir, "context")
    os.makedirs(editable_dir, exist_ok=True)
    os.makedirs(context_dir, exist_ok=True)

    prompt = STORE_AGENT_PROMPT.format(user_request=user_prompt)
    default_env = build_default_env()

    return {
        "name": "store-agent",
        "editable_dir": editable_dir,
        "context_dir": context_dir,
        "prompt": prompt,
        "editable_description": "Workspace for store agent operations",
        "context_description": "Skillberry Store context",
        "agent_type": "claude-code",
        "mode": "local",
        "output_zip": False,
        "agent_settings": {"env": default_env},
        "agent_max_turns": 50,
        "mcp_servers": {
            "skillberry-store": {
                "type": "sse",
                "url": f"http://localhost:{agent_mcp_port}/sse",
            }
        },
        "extra_summary_sections": [
            {
                "title": "Answer to User",
                "content": (
                    "Directly answer the user's original question. "
                    "Include any connection commands, URLs, or instructions "
                    "they need to use what you created."
                ),
            }
        ],
    }

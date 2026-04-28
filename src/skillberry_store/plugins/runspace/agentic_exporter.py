"""Agentic exporter: builds a RunspaceAgent request body for AI-driven skill creation."""

import logging
import os
import tempfile
from typing import Any, Dict, List, Optional

from skillberry_store.tools.anthropic.exporter import get_tool_extension

logger = logging.getLogger(__name__)


def build_context_directory(
    skill_dict: Dict[str, Any],
    tools: List[Dict[str, Any]],
    snippets: List[Dict[str, Any]],
    tool_modules: Optional[Dict[str, str]],
    base_dir: str,
) -> str:
    context_dir = os.path.join(base_dir, "context")
    tools_dir = os.path.join(context_dir, "tools")
    snippets_dir = os.path.join(context_dir, "snippets")
    os.makedirs(tools_dir, exist_ok=True)
    os.makedirs(snippets_dir, exist_ok=True)

    skill_info = _build_skill_info(skill_dict, tools, snippets)
    with open(os.path.join(context_dir, "skill_info.md"), "w", encoding="utf-8") as f:
        f.write(skill_info)

    for tool in tools:
        tool_name = tool["name"]
        ext = get_tool_extension(tool)
        content = ""
        if tool_modules and tool_name in tool_modules:
            content = tool_modules[tool_name]
        else:
            lang = tool.get("programming_language", "python")
            comment = "#" if lang.lower() in ("python", "py", "bash", "sh", "shell") else "//"
            content = f"{comment} Source code not available for tool: {tool_name}\n"
            logger.warning(f"No module content for tool '{tool_name}'")

        with open(os.path.join(tools_dir, f"{tool_name}{ext}"), "w", encoding="utf-8") as f:
            f.write(content)

    for snippet in snippets:
        snippet_name = snippet["name"]
        content = snippet.get("content", "")
        content_type = snippet.get("content_type", "text/plain")
        ext = ".md" if "markdown" in content_type else ".txt"
        with open(os.path.join(snippets_dir, f"{snippet_name}{ext}"), "w", encoding="utf-8") as f:
            f.write(content)

    return context_dir


def _build_skill_info(
    skill_dict: Dict[str, Any],
    tools: List[Dict[str, Any]],
    snippets: List[Dict[str, Any]],
) -> str:
    lines = []
    lines.append(f"# Skill: {skill_dict['name']}\n")
    lines.append(f"**Description:** {skill_dict.get('description', 'No description')}\n")
    lines.append(f"**Version:** {skill_dict.get('version', 'unknown')}\n")

    tags = skill_dict.get("tags") or []
    if isinstance(tags, list) and tags:
        lines.append(f"**Tags:** {', '.join(str(t) for t in tags)}\n")

    if tools:
        lines.append("\n## Tools\n")
        for tool in tools:
            lines.append(f"### {tool['name']}\n")
            lines.append(f"- **Description:** {tool.get('description', 'No description')}")
            lines.append(f"- **Language:** {tool.get('programming_language', 'unknown')}")

            params = tool.get("params")
            if isinstance(params, dict):
                properties = params.get("properties", {})
                required_params = params.get("required", [])
                if properties:
                    lines.append("- **Parameters:**")
                    for p_name, p_schema in properties.items():
                        if isinstance(p_schema, dict):
                            p_type = p_schema.get("type", "any")
                            p_desc = p_schema.get("description", "")
                        else:
                            p_type = "any"
                            p_desc = ""
                        p_required = "required" if p_name in required_params else "optional"
                        lines.append(f"  - `{p_name}` ({p_type}, {p_required}): {p_desc}")

            returns = tool.get("returns")
            if isinstance(returns, dict):
                r_type = returns.get("type", "any")
                r_desc = returns.get("description", "")
                lines.append(f"- **Returns:** {r_type} — {r_desc}")
            elif isinstance(returns, str) and returns:
                lines.append(f"- **Returns:** {returns}")

            lines.append("")

    if snippets:
        lines.append("\n## Snippets\n")
        for snippet in snippets:
            lines.append(f"### {snippet['name']}\n")
            lines.append(f"- **Description:** {snippet.get('description', 'No description')}")
            lines.append(f"- **Content type:** {snippet.get('content_type', 'text/plain')}")
            s_tags = snippet.get("tags") or []
            if isinstance(s_tags, list) and s_tags:
                lines.append(f"- **Tags:** {', '.join(str(t) for t in s_tags)}")
            lines.append("")

    return "\n".join(lines)


def build_editable_directory(base_dir: str) -> str:
    editable_dir = os.path.join(base_dir, "editable")
    os.makedirs(editable_dir, exist_ok=True)
    return editable_dir


def build_default_env() -> Dict[str, str]:
    ibm_base = os.environ.get("IBM_THIRD_PARTY_API_BASE", "")
    ibm_key = os.environ.get("IBM_THIRD_PARTY_API_KEY", "")
    return {
        "ANTHROPIC_BASE_URL": ibm_base if ibm_base else "<insert-your-anthropic-base-url>",
        "ANTHROPIC_AUTH_TOKEN": ibm_key if ibm_key else "<insert-your-auth-token>",
        "ANTHROPIC_MODEL": "claude-opus-4-6",
        "CLAUDE_CODE_SUBAGENT_MODEL": "claude-opus-4-6",
        "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1",
        "opusPlanEnabled": "true",
    }


def build_agent_prompt(skill_name: str) -> str:
    return f"""\
You are converting a skillberry-store skill into a high-quality Anthropic skill.

The context/ directory contains the complete source material for a skill called "{skill_name}":
- context/skill_info.md — Overview of the skill: its name, description, and a summary of every tool and snippet it contains (including parameter schemas).
- context/tools/ — The actual source code (.py/.sh) for each tool in the skill.
- context/snippets/ — The content of each snippet in the skill.

Your task: Create a complete, production-quality Anthropic skill in the editable/ directory.

## What to create

1. **SKILL.md** with YAML frontmatter:
   - `name`: Use "{skill_name}"
   - `description`: A clear, actionable description of when and how to use this skill. Make it slightly "pushy" so it triggers reliably — describe not just what it does, but the user contexts where it should activate.
   - Body: Usage instructions, workflow guidance, and explanations of what the skill provides.

2. **scripts/** directory with standalone tool scripts:
   - Convert each tool from context/tools/ into a standalone script with `argparse`.
   - Each script must be runnable as: `python scripts/tool_name.py --arg1 value1 --arg2 value2`
   - Preserve the core logic from the original source code but restructure for CLI use.
   - Add proper `if __name__ == "__main__":` blocks.
   - Include clear help text in the argparse description.
   - For bash tools, keep them as .sh scripts with proper argument parsing.

3. **references/** directory with documentation:
   - Convert each snippet from context/snippets/ into a markdown reference document.
   - Organize logically and add any cross-references between docs.

## Guidelines

- Read ALL files in context/ before starting. Understand the full picture first.
- The SKILL.md body should explain how to use each script, with examples.
- Keep scripts self-contained — each one should work independently.
- Preserve the original tool's functionality faithfully.
- Add error handling and input validation to scripts.
- Use the /skill-creator skill for guidance on best practices for Anthropic skill structure.

## Quality checklist

Before finishing, verify:
- [ ] SKILL.md has valid YAML frontmatter with name and description
- [ ] Every tool has a corresponding script in scripts/
- [ ] Every snippet has a corresponding reference in references/
- [ ] Each script has argparse and can be invoked from the command line
- [ ] SKILL.md body documents all scripts with usage examples
"""


def build_agent_request(
    skill_dict: Dict[str, Any],
    tools: List[Dict[str, Any]],
    snippets: List[Dict[str, Any]],
    tool_modules: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    skill_name = skill_dict["name"]

    base_dir = tempfile.mkdtemp(prefix=f"sbs_agentic_export_{skill_name}_")
    logger.info(f"Created agentic export workspace at: {base_dir}")

    context_path = build_context_directory(
        skill_dict, tools, snippets, tool_modules, base_dir
    )
    editable_path = build_editable_directory(base_dir)
    prompt = build_agent_prompt(skill_name)
    default_env = build_default_env()

    return {
        "name": f"agentic-export-{skill_name}",
        "editable_dir": str(editable_path),
        "context_dir": str(context_path),
        "prompt": prompt,
        "editable_description": "Empty directory — agent creates the Anthropic skill from scratch",
        "context_description": (
            f"Source code and metadata for the '{skill_name}' skill "
            "— tool source files, snippet content, and a skill_info.md summary"
        ),
        "preinstalled_skills": ["skill-creator"],
        "agent_type": "claude-code",
        "mode": "local",
        "output_zip": False,
        "agent_settings": {"env": default_env},
        "agent_max_turns": 50,
    }

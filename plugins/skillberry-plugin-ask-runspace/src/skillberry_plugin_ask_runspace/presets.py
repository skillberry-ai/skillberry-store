"""Example task presets that prefill the free-text request and skills list.

A preset is just a starting point: selecting one fills the textarea (``prompt``)
and the skills list (``skills``) on the client, both fully editable. There is no
server-side prompt composition — the free-text field IS the whole prompt.
"""
from typing import List, Dict, Union

PRESETS: List[Dict[str, Union[str, List[str]]]] = [
    # Generic option first: no guidance, the request is used verbatim.
    {"id": "custom", "label": "Anything — describe the task yourself",
     "prompt": "", "skills": []},
    {"id": "tool", "label": "Create a tool that…",
     "prompt": "Create a new tool that <describe it>. Implement it cleanly with a clear interface and a short usage note.",
     "skills": []},
    {"id": "skill", "label": "Create a skill that…",
     "prompt": "Create a new skill that <describe it>, following the Anthropic skill format (a SKILL.md plus supporting files).",
     "skills": ["https://github.com/anthropics/skills/tree/main/skills/skill-creator"]},
    {"id": "mcp", "label": "Build an MCP server that…",
     "prompt": "Build an MCP server that <describe it>, following the mcp-builder skill's conventions.",
     "skills": ["https://github.com/anthropics/skills/tree/main/skills/mcp-builder"]},
    {"id": "optimize", "label": "Optimize a skill…",
     "prompt": ("Optimize the skill in the editable directory for correctness, robustness, and clarity without "
                "changing its intended functionality. Read all reference material first, fix ambiguous tool "
                "descriptions and missing guardrails, and keep the result store-compatible (valid SKILL.md "
                "frontmatter, self-contained Python tools). Explain what you changed and why."),
     "skills": ["https://github.com/skillberry-ai/evo-graph"]},
    {"id": "research", "label": "Research and summarize…",
     "prompt": "Research <topic> and produce a concise, well-structured written summary.",
     "skills": []},
    {"id": "document", "label": "Write documentation for…",
     "prompt": "Write clear, accurate documentation for <subject>, with examples where helpful.",
     "skills": []},
    {"id": "debug", "label": "Debug / fix…",
     "prompt": "Investigate <problem>, find the root cause, fix it, and explain the fix.",
     "skills": []},
]

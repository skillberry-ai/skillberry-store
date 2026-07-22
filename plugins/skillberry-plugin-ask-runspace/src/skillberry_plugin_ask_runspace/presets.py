"""Example task presets that prefill the free-text request and skills list.

A preset is just a starting point: selecting one fills the textarea (``prompt``),
the skills list (``skills``), and any per-task environment overrides (``env``) on
the client, all fully editable. There is no server-side prompt composition — the
free-text field IS the whole prompt.
"""
from typing import Dict, List, Union

PRESETS: List[Dict[str, Union[str, List[str], Dict[str, str]]]] = [
    # Generic option first: no guidance, the request is used verbatim.
    {"id": "custom", "label": "Anything — describe the task yourself",
     "prompt": "", "skills": [], "env": {}},
    {"id": "optimize", "label": "Optimize a skill…",
     "prompt": ("Optimize the skill in the editable directory for correctness, robustness, and clarity without "
                "changing its intended functionality. Read all reference material first, fix ambiguous tool "
                "descriptions and missing guardrails, and keep the result store-compatible (valid SKILL.md "
                "frontmatter, self-contained Python tools). Explain what you changed and why."),
     "skills": ["https://github.com/skillberry-ai/evo-graph"],
     # Optimization benefits from the multi-agent team workflow, so turn on the
     # experimental agent-teams flag for this preset (merged into the agent env).
     "env": {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"}},
    {"id": "dream", "label": "Dream — improve an agent's skills from its trajectories",
     "prompt": ("Run a skill 'dreaming' pass on the agent trajectories in this request. Find "
                "where the agent struggled, repeated work, or errored, and which skills were "
                "involved, then improve them via the skillberry-store MCP.\n"
                "Behave AS IF the store never allows in-place updates: a skill name always "
                "resolves to its latest version (like git). So to change a skill, always "
                "create a NEW skill (new UUID) with the SAME name — never edit in place, never "
                "rename (no *_optimized).\n"
                "Do what the trajectories call for: new version of an involved skill, and/or a "
                "supporting snippet or genuinely new skill. Note a short rationale per change; "
                "make none if nothing warrants it."),
     "skills": [],
     # Dreaming reviews multiple trajectories and skills; the agent-teams workflow helps.
     "env": {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"}},
    {"id": "skill", "label": "Create a skill that…",
     "prompt": "Create a new skill that <describe it>, following the Anthropic skill format (a SKILL.md plus supporting files).",
     "skills": ["https://github.com/anthropics/skills/tree/main/skills/skill-creator"],
     "env": {}},
    {"id": "tool", "label": "Create a tool that…",
     "prompt": "Create a new tool that <describe it>. Implement it cleanly with a clear interface and a short usage note.",
     "skills": [], "env": {}},
    {"id": "research", "label": "Research and summarize…",
     "prompt": "Research <topic> and produce a concise, well-structured written summary.",
     "skills": [], "env": {}},
    {"id": "document", "label": "Write documentation for…",
     "prompt": "Write clear, accurate documentation for <subject>, with examples where helpful.",
     "skills": [], "env": {}},
    {"id": "debug", "label": "Debug / fix…",
     "prompt": "Investigate <problem>, find the root cause, fix it, and explain the fix.",
     "skills": [], "env": {}},
]

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
     "prompt": ("Run a skill 'dreaming' pass. You are given an agent's recent execution "
                "trajectories (inlined in this request, or fetched via an attached "
                "trajectories MCP). Study where the agent struggled, repeated work, or hit "
                "errors, and identify which of its skills were involved. Then improve them "
                "via the skillberry-store MCP.\n"
                "Store objects are IMMUTABLE and versioned like git: revising a skill under "
                "its EXISTING NAME produces a NEW VERSION with a new UUID whose parent is the "
                "previous version — the latest is resolved by name, and a specific version by "
                "UUID (stability, traceability, lineage). Keep the same name so it stays the "
                "same logical skill; do NOT invent a new name (e.g. no *_optimized).\n"
                "Do whatever the trajectories call for: revise an involved skill (new version, "
                "same name), and/or add supporting snippets or a genuinely new skill if that "
                "is the right fix. Record a short rationale per change, and make NO change "
                "when the trajectories don't justify one."),
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

"""Example task presets that seed the free-text request."""
from typing import List, Dict, Optional

PRESETS: List[Dict[str, str]] = [
    # Generic option first: no guidance, the request is used verbatim.
    {"id": "custom", "label": "Anything — describe the task yourself",
     "guidance": ""},
    {"id": "tool", "label": "Create a tool that…",
     "guidance": "Create a new tool. Implement it cleanly with a clear interface and a short usage note."},
    {"id": "skill", "label": "Create a skill that…",
     "guidance": "Create a new skill: a SKILL.md plus any supporting files, following the Anthropic skill format."},
    {"id": "optimize", "label": "Optimize a skill…",
     "guidance": "Optimize the described skill: improve its instructions, structure, and tooling for reliability and clarity. Explain what you changed and why."},
    {"id": "research", "label": "Research and summarize…",
     "guidance": "Research the topic and produce a concise, well-structured written summary."},
    {"id": "improve", "label": "Refactor / improve…",
     "guidance": "Improve the described code or content; explain what you changed and why."},
    {"id": "document", "label": "Write documentation for…",
     "guidance": "Write clear, accurate documentation for the described subject, with examples where helpful."},
    {"id": "debug", "label": "Debug / fix…",
     "guidance": "Investigate the described problem, find the root cause, fix it, and explain the fix."},
]

_BY_ID = {p["id"]: p for p in PRESETS}


def compose_prompt(preset_id: Optional[str], request: str) -> str:
    """Combine an optional preset's guidance with the user's free-text request.

    A preset with empty guidance (e.g. the generic "custom" option) — or no
    preset at all — uses the request verbatim.
    """
    request = (request or "").strip()
    preset = _BY_ID.get(preset_id or "")
    if preset and preset.get("guidance", "").strip():
        return f"{preset['guidance']}\n\nUser request:\n{request}"
    return request

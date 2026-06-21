"""Example task presets that seed the free-text request."""
from typing import List, Dict, Optional

PRESETS: List[Dict[str, str]] = [
    {"id": "tool", "label": "Create a tool that…",
     "guidance": "Create a new tool. Implement it cleanly with a clear interface and a short usage note."},
    {"id": "skill", "label": "Create a skill that…",
     "guidance": "Create a new skill: a SKILL.md plus any supporting files, following the Anthropic skill format."},
    {"id": "research", "label": "Research and summarize…",
     "guidance": "Research the topic and produce a concise, well-structured written summary."},
    {"id": "improve", "label": "Refactor / improve…",
     "guidance": "Improve the described code or content; explain what you changed and why."},
]

_BY_ID = {p["id"]: p for p in PRESETS}


def compose_prompt(preset_id: Optional[str], request: str) -> str:
    """Combine an optional preset's guidance with the user's free-text request."""
    request = (request or "").strip()
    preset = _BY_ID.get(preset_id or "")
    if preset:
        return f"{preset['guidance']}\n\nUser request:\n{request}"
    return request

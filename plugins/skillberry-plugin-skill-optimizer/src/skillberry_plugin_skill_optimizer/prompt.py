"""Optimization prompt builder for the Skill Optimizer RunSpace session."""

from __future__ import annotations

import json
from typing import Any, Dict

REQUIRED_OUTPUTS_FILENAME = "required_outputs.json"

REQUIRED_OUTPUTS_TEMPLATE: Dict[str, Any] = {
    "skill_name": "",
    "skill_description": "",
    "optimization_rationale": "",
    "issues_addressed": [],
    "tools_added": [],
    "tools_modified": [],
    "tools_removed": [],
    "snippets_added": [],
    "snippets_modified": [],
    "snippets_removed": [],
    "ready_for_deployment": True,
}


def build_runspace_prompt(
    *,
    has_metadata: bool = False,
    has_trajectories: bool = False,
    has_additional_context: bool = False,
) -> str:
    """Build the optimization prompt for RunspaceAgent."""
    # context/knowledge/ is always present — it's bundled with the optimizer
    inventory_lines = [
        "- context/knowledge/ — READ THIS FIRST. Contains three files:\n"
        "    01-skillberry-store-format.md  — complete format rules for the SkillBerry Store importer\n"
        "    02-skill-best-practices.md     — how to write high-quality skill instructions and tools\n"
        "    03-skill-description-optimization.md — how to write descriptions that trigger reliably",
    ]
    if has_metadata:
        inventory_lines.append(
            "- context/skill_metadata.json — skill tags, extra metadata, "
            "and tool/snippet descriptions."
        )
    if has_trajectories:
        inventory_lines.append(
            "- context/trajectories/ — execution trajectories from prior skill runs "
            "(each entry has a `reward` value; higher = better outcome)."
        )
    if has_additional_context:
        inventory_lines.append(
            "- context/additional_context/ — additional context "
            "(documentation, requirements, examples, domain knowledge, etc.)."
        )
    inventory = "\n".join(inventory_lines)

    if has_trajectories:
        analyze_block = """\
HOW TO ANALYZE TRAJECTORIES:
1. Read the trajectories and their `reward` values. Higher reward = better outcome.
2. Study SUCCESSFUL trajectories (high reward) — understand what to preserve.
3. Study FAILED trajectories (low reward) — find WHERE and WHY the agent went wrong
   (wrong tool, wrong arguments, unnecessary steps, policy violations, etc.).
4. Cluster strengths (preserve) and weaknesses (fix).
5. Improve the skill GENERICALLY so it transfers to unseen/production tasks.
   Do NOT overfit to the specific trajectories — fix the underlying behavior:
   - Remove tools made redundant by better ones.
   - Add guardrails/checks to prevent the failure modes you found.
   - Add helper/composite tools that simplify the agent's job.
   - Clarify tool descriptions/signatures so the agent picks the right tool
     with correct arguments.
"""
    else:
        analyze_block = """\
HOW TO ANALYZE:
Read the skill content and any context provided. Improve clarity, correctness, and
completeness. Look for ambiguous tool descriptions, missing guardrails, redundant
tools, or structural issues that would cause an agent to misuse the skill. Remove
tools that are unclear or redundant — a smaller, sharper skill is better than a
large bloated one.
"""

    required_outputs_pretty = json.dumps(REQUIRED_OUTPUTS_TEMPLATE, indent=2)

    return f"""\
You are optimizing a Skillberry skill. The editable directory IS the current skill,
exported from the Skillberry Store in Anthropic format. Your job: improve it, then
leave it importable back into the store.

CONTEXT LAYOUT:
{inventory}

{analyze_block}
=== SKILLBERRY STORE ANTHROPIC SKILL FORMAT (MUST FOLLOW) ===

The editable directory is re-imported into the Skillberry Store after you finish.
Keep it store-compatible:

PYTHON FILES (.py) -> TOOLS:
- Each .py file is AST-parsed; every top-level `def` becomes a separate tool.
- Function name -> tool name; docstring -> description; type annotations +
  docstring Args -> parameter schema.
- A .py file with no functions becomes one tool named after the file.

NON-CODE FILES (.md, .txt, .json, ...) -> SNIPPETS:
- All non-Python files become read-only reference snippets.
- The SKILL.md body (everything after the YAML frontmatter) also becomes a snippet.

SKILL.md FRONTMATTER RULES:
- Must start with a `---`-delimited YAML frontmatter block.
- ONLY `name` and `description` are recognized — do not add other fields.
- `name` must be kebab-case, max 64 characters.
- `description` must be present, max 1024 characters.

PYTHON FILE FORMAT RULES:
- Each .py file must be self-contained: only stdlib imports + injected helpers.
- No relative or cross-file imports (`from scripts.foo import bar` is FORBIDDEN).
- Runtime helpers are INJECTED into execution scope — call them directly,
  do NOT import them.

PRESERVE STRUCTURE:
- Do NOT rename, move, or delete existing files.
- Keep the output directory structure the same as the input.
- Do NOT leave temporary files in the directory — they will be imported.
- Keep SKILL.md frontmatter valid at all times.

SKILL NAME:
- If you made meaningful changes, update SKILL.md `name` to a new kebab-case
  name (max 64 characters) that hints at what changed.
- Put the SAME value in `skill_name` in required_outputs.json.
- IMPORTANT: only change the NAME VALUE inside SKILL.md — do NOT create
  subdirectories, do NOT move SKILL.md, do NOT rename the editable directory.

=== REQUIRED OUTPUT CONTRACT ===
The editable directory contains a file named `{REQUIRED_OUTPUTS_FILENAME}`. You MUST
open it and fill in EVERY field describing the changes you made, then save it.
The optimizer reads this file to record what changed. Template:

{required_outputs_pretty}

Field meanings:
- skill_name: the (possibly updated) kebab-case skill name from SKILL.md frontmatter.
- skill_description: the skill description from SKILL.md frontmatter.
- optimization_rationale: a concise explanation of what you changed and why.
- issues_addressed: list of the failure modes / issues you fixed.
- tools_added / tools_modified / tools_removed: function names added, changed, removed.
- snippets_added / snippets_modified / snippets_removed: non-code files changed.
- ready_for_deployment: true if the skill is valid and ready to upload.

`{REQUIRED_OUTPUTS_FILENAME}` is a temporary contract file — the optimizer removes it
before importing the skill back into the store.
"""

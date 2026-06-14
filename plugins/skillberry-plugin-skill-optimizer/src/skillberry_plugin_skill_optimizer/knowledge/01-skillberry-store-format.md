# SkillBerry Store — Skill Format Specification

This file defines the exact format required for a skill that will be imported into
the SkillBerry Store. **Every rule here is enforced by the importer — violations
will cause import failure or silent data corruption.**

---

## Directory Structure

A skill exported from the SkillBerry Store looks like this on disk:

```
<skill-name>/
├── SKILL.md          # Required: frontmatter + instructions body
├── scripts/          # Optional: Python tool modules (.py files)
├── references/       # Optional: documentation snippets
├── assets/           # Optional: templates, data files
└── ...               # Any other non-Python files become snippets
```

---

## SKILL.md Format

### Frontmatter

`SKILL.md` MUST begin with a `---`-delimited YAML frontmatter block. Only two
fields are recognised by the SkillBerry Store importer:

| Field         | Required | Constraints                                                      |
|---------------|----------|------------------------------------------------------------------|
| `name`        | Yes      | Kebab-case, max 64 characters. Lowercase letters, numbers, hyphens only. Must not start or end with a hyphen. No consecutive hyphens. |
| `description` | Yes      | Max 1024 characters. Non-empty. Describes what the skill does and when to use it. |

**Do NOT add any other fields to the frontmatter.** Extra fields are silently
ignored but pollute the skill definition.

Minimal example:
```yaml
---
name: my-skill
description: Extracts structured data from invoices. Use when working with PDF or image invoices.
---
```

### `name` field rules

- 1–64 characters
- Only `a-z`, `0-9`, and `-`
- Must not start or end with `-`
- Must not contain `--`
- Must match the parent directory name
- If you made meaningful changes, update `name` to hint at the improvement
  (e.g. `invoice-parser-guardrails`). Keep it short — 2–4 words.

### `description` field rules

- 1–1024 characters (hard limit enforced by importer)
- Should describe **what the skill does AND when to use it**
- Use imperative phrasing: "Use this skill when…" or "Extracts… when the user…"
- Include specific keywords that help agents recognise relevant tasks
- Err on the side of being specific about scope boundaries

**Good example:**
```yaml
description: >
  Extracts text, tables, and form fields from PDF files. Use when working with
  PDF documents, invoices, contracts, or scanned forms — even if the user
  doesn't explicitly say "PDF."
```

**Poor example:**
```yaml
description: Helps with PDFs.
```

### Body content

The Markdown body (everything after the closing `---`) becomes a **snippet** in
the SkillBerry Store. It contains the instructions the agent follows. There are
no format restrictions, but effective bodies include:

- Step-by-step instructions (numbered lists)
- Gotchas (non-obvious edge cases the agent will get wrong without guidance)
- Working examples of inputs and outputs
- Checklists for multi-step workflows

Keep the body under 500 lines. Move detailed reference material to separate files
in `references/` and tell the agent exactly when to load them.

---

## How the SkillBerry Importer Classifies Files

The importer classifies every file in the skill directory by **extension**,
not by directory name.

### Python files (`.py`) → Tools

Every `.py` file is AST-parsed. Each **top-level `def`** becomes a separate tool:

- Function name → tool name
- Docstring → tool description
- Type annotations + docstring `Args:` section → parameter schema

A `.py` file with **no functions** becomes one tool named after the file.

**Critical rules for Python files:**

1. Each `.py` file must be **self-contained**: only stdlib imports plus injected
   helpers. The store executes each file as a flat script — there is no
   module/package system.
2. **Relative and cross-file imports are FORBIDDEN:**
   ```python
   # NEVER do this — breaks at runtime
   from scripts.helpers import call_api
   import scripts.utils
   ```
3. Runtime helpers (e.g. `call_api`, `store_result`) are **injected into the
   execution scope** by the store before your code runs. Call them directly —
   do NOT import them.
4. Each function should have a clear docstring describing what it does, its
   parameters, and its return value. This becomes the tool's description in the
   store and is what agents use to decide whether to call the tool.

**Good tool function:**
```python
def extract_invoice_total(invoice_text: str) -> float:
    """Extract the total amount due from invoice text.

    Args:
        invoice_text: Raw text content of an invoice document.

    Returns:
        The total amount due as a float.
    """
    # implementation
```

### Non-Python files → Snippets

All non-Python files (`.md`, `.txt`, `.json`, `.yaml`, `.csv`, etc.) become
**read-only reference snippets** in the store. This includes:

- The `SKILL.md` body (the instructions)
- Any files in `references/`, `assets/`, or other subdirectories
- Configuration files, templates, schemas

---

## Preserve Structure (Critical)

When optimizing a skill, you are editing the skill **in place** — the same
directory will be re-imported after you finish. Follow these rules:

- **Do NOT rename, move, or delete existing files.** Renaming changes tool/snippet
  identity and breaks the import/export round-trip.
- **Do NOT create subdirectories** that don't already exist, unless you are
  adding reference material the agent can load on demand.
- **Do NOT leave temporary files** in the directory — everything gets imported.
- **Do NOT add `__init__.py`** or any Python packaging files.
- Keep `SKILL.md` at the **top level** of the skill directory at all times.

---

## Skill Name — Updating After Optimization

If you made meaningful improvements, update the `name` field in `SKILL.md`
frontmatter to a new kebab-case name that concisely describes what changed:

- `invoice-parser` → `invoice-parser-guardrails`
- `data-analyst` → `data-analyst-chart-fix`

Rules:
- Max 64 characters — keep it short (2–4 words)
- Only change the **value** inside `SKILL.md` (and in `required_outputs.json`)
- **Do NOT** rename the directory, create a new subdirectory, or move `SKILL.md`

---

## Required Output Contract

The optimization session produces a `required_outputs.json` file in the skill
directory. You MUST fill in every field before finishing. The optimizer reads
this to record what changed and attach it to the new skill's metadata in the
store. See the main prompt for the template and field definitions.

# Best Practices for Writing and Optimizing Skills

Source: agentskills.io — adapted for the SkillBerry Store context.

---

## Start from Real Expertise

A common failure mode: using an LLM to generate a skill without domain-specific
context. The result is vague, generic instructions ("handle errors appropriately",
"follow best practices") rather than the specific patterns, edge cases, and
conventions that make a skill valuable.

**When optimizing, look for:**
- Generic advice that could be replaced with specific, concrete instructions
- Missing edge cases that real runs would surface
- Over-broad instructions that cause the agent to pursue unproductive paths

---

## Spending Context Wisely

The skill's `SKILL.md` body loads into the agent's context window alongside
conversation history, system context, and other active skills. Every token
competes for the agent's attention.

### Add what the agent lacks, omit what it knows

Focus on what the agent *wouldn't* know without the skill: project-specific
conventions, domain procedures, non-obvious edge cases, specific APIs or tools.
You don't need to explain what a PDF is or how HTTP works.

**Too verbose — agent already knows this:**
```markdown
## Extract PDF text

PDF (Portable Document Format) files are a common file format that contains
text, images, and other content. To extract text from a PDF, you'll need to
use a library. pdfplumber is recommended because it handles most cases well.
```

**Better — jumps straight to what the agent wouldn't know:**
```markdown
## Extract PDF text

Use pdfplumber for text extraction. For scanned documents, fall back to
pdf2image with pytesseract.
```

Ask about each piece of content: "Would the agent get this wrong without this
instruction?" If the answer is no, cut it.

### Keep SKILL.md under 500 lines

Move detailed reference material to separate files. Tell the agent *when* to
load each file — "Read `references/api-errors.md` if the API returns a
non-200 status code" — rather than a generic "see references/ for details."

---

## Calibrating Control

Not every part of a skill needs the same level of prescriptiveness.

### Give freedom when approaches are equally valid

For flexible tasks, explaining *why* is more effective than rigid directives.
An agent that understands the purpose makes better context-dependent decisions.

```markdown
## Code review process
1. Check all database queries for SQL injection (use parameterized queries)
2. Verify authentication checks on every endpoint
3. Look for race conditions in concurrent code paths
4. Confirm error messages don't leak internal details
```

### Be prescriptive for fragile operations

When a specific sequence must be followed or consistency matters:

```markdown
## Database migration

Run exactly this sequence:
```bash
python scripts/migrate.py --verify --backup
```
Do not modify the command or add additional flags.
```

### Provide defaults, not menus

Pick a default approach and mention alternatives briefly:

**Too many options:**
```markdown
You can use pypdf, pdfplumber, PyMuPDF, or pdf2image...
```

**Clear default with escape hatch:**
```markdown
Use pdfplumber for text extraction. For scanned PDFs requiring OCR,
use pdf2image with pytesseract instead.
```

---

## Patterns for Effective Instructions

### Gotchas sections (highest value)

The highest-value content in many skills is a list of gotchas — environment-specific
facts that defy reasonable assumptions:

```markdown
## Gotchas

- The `users` table uses soft deletes. Queries must include
  `WHERE deleted_at IS NULL` or results will include deactivated accounts.
- The user ID is `user_id` in the database, `uid` in the auth service,
  and `accountId` in the billing API. All three refer to the same value.
- The `/health` endpoint returns 200 even if the database connection is down.
  Use `/ready` to check full service health.
```

When an agent makes a mistake, add the correction to the gotchas section. This
is one of the most direct ways to improve a skill iteratively.

### Templates for output format

When you need the agent to produce output in a specific format, provide a template.
Agents pattern-match well against concrete structures:

```markdown
## Report structure

Use this template:
```markdown
# [Analysis Title]
## Executive summary
[One-paragraph overview of key findings]
## Key findings
- Finding 1 with supporting data
## Recommendations
1. Specific actionable recommendation
```
```

### Checklists for multi-step workflows

```markdown
## Processing workflow
- [ ] Step 1: Analyze the input (run `scripts/analyze.py`)
- [ ] Step 2: Create field mapping (edit `fields.json`)
- [ ] Step 3: Validate mapping (run `scripts/validate.py`)
- [ ] Step 4: Execute (run `scripts/process.py`)
- [ ] Step 5: Verify output (run `scripts/verify.py`)
```

### Validation loops

```markdown
## Editing workflow
1. Make your edits
2. Run validation: `python scripts/validate.py output/`
3. If validation fails: fix the issues and run validation again
4. Only proceed when validation passes
```

### Procedures over declarations

A skill should teach the agent *how to approach* a class of problems, not *what
to produce* for a specific instance:

**Specific answer — only useful for this exact task:**
```markdown
Join the `orders` table to `customers` on `customer_id`, filter where
`region = 'EMEA'`, and sum the `amount` column.
```

**Reusable method — works for any analytical query:**
```markdown
1. Read the schema from `references/schema.yaml` to find relevant tables
2. Join tables using the `_id` foreign key convention
3. Apply filters from the user's request as WHERE clauses
4. Aggregate numeric columns and format as a markdown table
```

---

## Designing Coherent Units

Skills scoped too narrowly force multiple skills to load for a single task.
Skills scoped too broadly become hard to activate precisely.

A skill for querying a database and formatting results may be one coherent unit.
A skill that also covers database administration is probably trying to do too much.

When optimizing: resist the urge to add more tools/functions. Removing a redundant
or unclear tool is a valid, often better, optimization. A smaller, sharper skill
outperforms a large bloated one.

---

## Tool Function Quality

Since `.py` files become tools in the SkillBerry Store, tool quality matters.

**Good tool functions:**
- Have a single, clear responsibility
- Include a docstring describing what they do, their parameters, and return value
- Use type annotations on all parameters and return values
- Handle edge cases gracefully with informative error messages
- Are self-contained (no cross-file imports)

**Red flags to fix when optimizing:**
- Functions doing multiple unrelated things → split them
- Vague parameter names (`data`, `input`, `value`) → use descriptive names
- Missing docstrings → add them (the docstring becomes the tool description)
- Overly broad `except Exception` → catch specific exceptions
- Functions that are never called in practice → remove them

---

## Progressive Disclosure

Structure skills to take advantage of how agents load content:

1. **Metadata (~100 tokens)**: `name` and `description` — loaded at startup
2. **Instructions (<5000 tokens recommended)**: full `SKILL.md` body — loaded on activation
3. **Resources (as needed)**: files in `scripts/`, `references/`, `assets/` — loaded on demand

Tell the agent exactly when to load reference files:
```markdown
If the API returns a non-200 status, read `references/error-codes.md` for
the complete error reference before retrying.
```

This lets the agent load context on demand instead of up front, keeping the
context window lean during normal runs.

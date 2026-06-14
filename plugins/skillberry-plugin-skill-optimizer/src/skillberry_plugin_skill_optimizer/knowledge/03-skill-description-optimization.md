# Optimizing Skill Descriptions

Source: agentskills.io — adapted for the SkillBerry Store context.

The `description` field in `SKILL.md` frontmatter is the primary mechanism agents
use to decide whether to load a skill. An under-specified description means the
skill won't trigger when it should; an over-broad description means it triggers
when it shouldn't.

---

## How Skill Triggering Works

Agents use **progressive disclosure**: at startup, they load only `name` and
`description` — just enough to know when a skill might be relevant. When a task
matches, the agent reads the full `SKILL.md` into context.

The description carries the **entire burden of triggering**. If it doesn't convey
when the skill is useful, the agent won't reach for it.

Important nuance: agents typically only activate skills for tasks requiring
knowledge or capabilities beyond what they can handle alone. A simple "read this
PDF" may not trigger a PDF skill even with a perfect description — the agent
handles it with basic tools. Specialised knowledge, domain workflows, and uncommon
formats are where description quality makes the difference.

---

## Principles for Effective Descriptions

### Use imperative phrasing

Frame as an instruction to the agent: "Use this skill when…" rather than
"This skill does…" The agent is deciding whether to act, so tell it when to act.

### Focus on user intent, not implementation

Describe what the user is trying to achieve, not the skill's internal mechanics.
The agent matches against what the user asked for.

### Err on the side of being pushy

Explicitly list contexts where the skill applies, including cases where the user
doesn't name the domain directly:

```yaml
description: >
  Analyze CSV and tabular data files — compute summary statistics, add derived
  columns, generate charts, and clean messy data. Use this skill when the user
  has a CSV, TSV, or Excel file and wants to explore, transform, or visualize
  the data, even if they don't explicitly mention "CSV" or "analysis."
```

### Keep it concise

A few sentences to a short paragraph. The hard limit is 1024 characters.

---

## Before vs. After Examples

```yaml
# Before — too vague, won't trigger reliably
description: Process CSV files.

# After — specific about what it does AND when to use it
description: >
  Analyze CSV and tabular data files — compute summary statistics,
  add derived columns, generate charts, and clean messy data. Use this
  skill when the user has a CSV, TSV, or Excel file and wants to
  explore, transform, or visualize the data, even if they don't
  explicitly mention "CSV" or "analysis."
```

```yaml
# Before — generic, doesn't convey scope
description: Help with code review.

# After — specific domains, clear trigger conditions
description: >
  Review Python code for security vulnerabilities, SQL injection risks,
  authentication gaps, and race conditions. Use when asked to review,
  audit, or check code quality — especially for backend services handling
  user data or authentication flows.
```

```yaml
# Before — too narrow, misses indirect triggers
description: Extract text from PDF files.

# After — covers indirect triggers and related tasks
description: >
  Extract text, tables, and form fields from PDF documents. Fill PDF forms
  programmatically. Merge or split PDF files. Use when working with PDF
  documents, invoices, contracts, scanned forms, or any task involving
  PDF processing — even if the user says "document" instead of "PDF."
```

---

## Debugging a Description That Isn't Triggering

The fastest diagnostic: **ask Claude directly**.

```
"When would you use the [skill name] skill?"
```

Claude will quote the description back and explain when it would reach for the skill. Read its answer — if the trigger conditions it names don't match the tasks you intended, the description is the problem. Adjust and repeat.

This single technique can save many cycles of trial-and-error testing.

---

## Common Description Failures

### Too narrow — misses indirect phrasing
The user says "my boss wants a chart from this data file" — the skill's
description only mentions "CSV analysis." The agent doesn't connect the dots.

**Fix:** Add phrases that cover how users actually ask, not just the technical term.

### Too broad — triggers on irrelevant tasks
A database query skill triggers when the user asks to "write a Python script
that reads a CSV and uploads rows to Postgres" — not what the skill is for.

**Fix:** Add **negative triggers** that explicitly name what the skill does not cover. When an alternative skill exists, name it:

```yaml
description: >
  Advanced statistical analysis and machine learning on CSV and tabular data.
  Use when the user needs modeling, regression, clustering, or statistical
  summaries. Do NOT use for simple data exploration or chart generation
  (use the data-viz skill instead).
```

Negative triggers are especially useful when two related skills share keywords and compete for the same queries. Naming the alternative in the "Do NOT use" clause gives the agent a concrete redirect.

### Implementation focus instead of user intent
"Uses pdfplumber to extract text via AST parsing" — the agent doesn't match
this against "I need to pull the numbers from this invoice."

**Fix:** Describe what the user is trying to accomplish, not how the skill works.

### Missing trigger keywords
A skill for working with Kubernetes has no mention of "k8s", "pods",
"deployments", or "kubectl" — only "container orchestration."

**Fix:** Include the vocabulary users actually use, including abbreviations and
informal terms.

---

## Evaluating Description Quality

When optimizing a description, consider these test queries mentally:

**Should trigger:**
- A casual phrasing that describes the need without naming the domain
  ("my boss wants a chart from this data file")
- A terse prompt with the domain term ("analyze my sales CSV")
- A context-heavy prompt with file paths and column names
- A multi-step request where the skill is only one part

**Should NOT trigger (near-misses):**
- Queries that share keywords but need something different
  ("write a Python script that reads a CSV and uploads rows to Postgres"
  should not trigger a CSV *analysis* skill)
- General queries that the agent can handle alone
  ("what's the weather today?")

---

## The Optimization Loop

When a description isn't working:

1. **If should-trigger queries are failing** — the description is too narrow.
   Broaden scope or add context about when the skill is useful.

2. **If should-not-trigger queries are false-triggering** — the description is
   too broad. Add specificity about what the skill does *not* do.

3. **Avoid keyword overfitting** — don't add the exact keywords from failed queries.
   Find the general category those queries represent and address that.

4. **Try structural changes** if incremental tweaks aren't working. A different
   framing may break through where refinement can't.

5. **Check the 1024-character limit** — descriptions tend to grow during
   optimization. Trim if needed.

---

## Applying the Result

1. Update the `description` field in `SKILL.md` frontmatter
2. Verify it's under 1024 characters
3. Verify `name` is still accurate (update if the skill's scope changed)
4. The description should answer: "If an agent sees only this one sentence/paragraph,
   would it know exactly when to reach for this skill?"

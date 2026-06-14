# Optimizing Snippets

Snippets in the SkillBerry Store are **read-only textual reference material** — the
SKILL.md body, documentation files, schemas, templates, and any non-Python file in
the skill directory. Agents load them to understand context, follow procedures, or
look up reference data.

A snippet is well-optimized when an agent reads it and gets exactly the information
it needs — no more, no less — to act correctly on the first attempt.

---

## Diagnose Before You Edit

The most common optimization mistake is editing text based on what *looks* wrong,
rather than what actually *causes failures*.

Before changing anything, ask:

1. **What task was the agent trying to do?**
2. **At which step did behavior diverge from intent?**
3. **Was the failure caused by missing information, ambiguous information, or
   information the agent ignored?**

These are three different problems requiring three different fixes:

| Failure cause | Fix |
|---|---|
| Missing information | Add the specific fact, example, or constraint that was absent |
| Ambiguous information | Replace the vague phrase with a concrete, specific one |
| Information ignored | Move the critical point earlier; restructure so it can't be skipped |

Editing text without diagnosing the failure often produces longer snippets that
still fail for the same underlying reason.

---

## Signals a Snippet Needs Work

A snippet is underperforming when execution traces show:

- The agent tried multiple approaches before finding one that works (instructions
  are vague — the agent is searching)
- The agent followed the instructions literally but produced a wrong result (the
  instructions describe the wrong thing)
- The agent skipped steps in a multi-step procedure (the structure doesn't convey
  dependencies clearly enough)
- The agent made a mistake you had to correct, and the correction isn't in the
  snippet yet
- The same edge case fails repeatedly across different runs (a known gotcha is
  undocumented)

---

## Targeted Mutations

When you've diagnosed the problem, apply the smallest change that fixes it.

### From generic to specific

Vague instructions cause the agent to improvise. Replace them with concrete,
domain-specific guidance.

**Before:**
```
Handle errors appropriately and return a useful message.
```

**After:**
```
If the API returns 429, wait 2 seconds and retry once. If it returns 5xx,
raise ValueError("service unavailable"). Do not expose raw HTTP status codes
in the error message.
```

### From description to example

When the intended output format or behavior is hard to describe, show it:

**Before:**
```
Format the result as a summary with key findings.
```

**After:**
```
Format the result as:

## Summary
[One sentence describing overall outcome]

## Key findings
- Finding 1: [specific data point]
- Finding 2: [specific data point]
```

### From implied to explicit

Don't assume the agent will infer constraints. State them:

**Before:**
```
Query the database for recent orders.
```

**After:**
```
Query the `orders` table. Always include `WHERE deleted_at IS NULL` — the
table uses soft deletes and omitting this filter returns deactivated records.
Limit to the last 90 days unless the user specifies otherwise.
```

### From one long block to layered disclosure

If a snippet is long, the agent may read the beginning and skip the rest. Structure
so that critical information comes first and reference material comes later:

```markdown
## Quick reference
[3-5 lines covering the most common case — agent can stop here for simple tasks]

## Full specification
[Detailed rules and edge cases — agent reads this when the quick reference isn't enough]

## Error reference
[What specific errors mean and how to resolve them]
```

---

## Gotchas: The Highest-Value Content

The most impactful content in any snippet is a list of things the agent will get
wrong without being told. These are not general best practices — they are specific
corrections that real execution failures have surfaced.

Good gotchas are:
- **Concrete**: name the specific field, endpoint, value, or behavior
- **Actionable**: tell the agent what to do, not just what not to do
- **Short**: one or two lines each; a list of five sharp gotchas beats a paragraph
  of caveats

**Example gotchas section:**
```markdown
## Gotchas

- The API returns `200 OK` even for validation failures — always check
  `response.json()["status"]`, not the HTTP status code.
- `user_id` in this API is a string UUID, not an integer. Passing an int
  causes a silent 400 with no error message.
- The `created_at` field is in Unix milliseconds, not seconds. Divide by
  1000 before passing to `datetime.fromtimestamp()`.
```

When an execution trace reveals a mistake, add the correction to the gotchas
section immediately. Do not wait for a second failure.

---

## What to Remove

Snippets accumulate content over time. Remove content that:

- Explains concepts the agent already knows from training (what JSON is, how
  HTTP works, what a primary key does)
- Repeats information already stated elsewhere in the skill
- Covers edge cases that never occur in practice
- Uses vague filler language ("make sure to", "be careful to", "try to") —
  replace with a specific instruction or remove entirely

A shorter snippet that covers only what the agent lacks is more effective than
a comprehensive one the agent will skim.

---

## Templates as Snippets

When the skill requires the agent to produce output in a specific format, a
template snippet is more reliable than a prose description of the format.

Store the template in a separate file (e.g., `assets/report-template.md`) and
reference it conditionally in SKILL.md:

```markdown
When producing a report, use the template in `assets/report-template.md`.
Load it only when the task requires a formatted report output.
```

This keeps SKILL.md lean while making the template available on demand.

---

## Checklist Before Finalising a Snippet

- [ ] Does every instruction say *what to do*, not just *what to consider*?
- [ ] Is each gotcha concrete enough that the agent couldn't misinterpret it?
- [ ] Does the structure put the most-needed information first?
- [ ] Have you removed content the agent already knows from training?
- [ ] If there's an example, does it match the actual expected format exactly?
- [ ] If there's a multi-step procedure, are the steps numbered with explicit
      dependencies noted?
- [ ] Is the snippet under 300 lines? If not, does the excess belong in a
      separate reference file?

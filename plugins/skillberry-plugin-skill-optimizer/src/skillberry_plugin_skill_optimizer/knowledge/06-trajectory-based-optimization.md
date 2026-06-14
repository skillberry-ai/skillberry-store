# Trajectory-Based Skill Optimization

When execution trajectories are provided in `context/trajectories/`, they are your
most valuable optimization signal. Trajectories show exactly what happened when an
agent used this skill in production — which tools were called, in what order, with
what arguments, and whether the task succeeded or failed.

**Use trajectories as ground truth.** Don't speculate about what might go wrong;
read what actually went wrong.

---

## What a Trajectory Contains

Each trajectory is a complete record of one agent session. It contains:

- **Messages**: the turn-by-turn conversation — user requests, assistant responses,
  tool calls, tool results, and system messages
- **Tool calls**: every tool invoked, with the exact arguments passed
- **Tool results**: what each tool returned (or what error it raised)
- **Reward / outcome**: a score (0.0–1.0) or pass/fail indicating whether the
  agent achieved the goal. Higher reward = better outcome.
- **Metadata**: optional context such as task domain, task ID, or timestamps

When a trajectory has a reward field, treat it as your primary signal:
- `reward ≥ 0.8` — successful run; study what made it work
- `reward ≤ 0.3` — failed run; diagnose the root cause
- `0.3 < reward < 0.8` — partial success; identify what was achieved vs. missed

---

## Reading a Single Trajectory

Before analysing patterns across many trajectories, understand each one fully.
For every trajectory, determine:

**1. What was the agent trying to do?**
Read the user's initial message and any goal statement.

**2. Did it succeed?**
Check the reward score, the final assistant message, or any explicit outcome marker.

**3. Where did things go wrong (or right)?**
Step through the tool calls in order:
- Which tools were called and in what sequence?
- Were the arguments correct and complete?
- Did any tool return an error? What was the error message?
- Did the agent recover from errors or give up?
- Were there unnecessary or redundant tool calls?
- Was anything called in the wrong order?

**4. What specific message IDs mark the key moments?**
Note the message where the failure began, the message where a recovery happened,
or the message that produced the decisive correct result. These are your evidence
anchors for targeted edits.

---

## Evaluating Trajectories Across Seven Dimensions

Not all failures are equal. For each trajectory, score these dimensions:

| Dimension | Question | What 0 looks like | What 1 looks like |
|---|---|---|---|
| **Task success** | Did the agent complete the goal? | Gave up or wrong outcome | Fully achieved the user's goal |
| **Tool selection** | Did the agent pick the right tools? | Used wrong tools, missed the right ones | Always chose the correct tool for each step |
| **Parameter quality** | Were tool arguments correct? | Fabricated parameters, wrong types, out-of-range values | All arguments valid and appropriate |
| **Plan efficiency** | Were steps minimal and direct? | Many redundant or circular calls | Reached the goal in the fewest reasonable steps |
| **Policy compliance** | Were constraints and rules followed? | Violated stated policies | Fully respected all policies |
| **Error recovery** | How were errors handled? | Gave up on first error | Diagnosed errors and recovered gracefully |
| **Task complexity** | How hard was this task? | Trivial one-step task | Multi-step task requiring judgment |

This framework helps you identify *which dimension* to fix. A skill with poor tool
selection needs different changes than one with poor parameter quality.

---

## Handling Large Numbers of Trajectories

When dozens or hundreds of trajectories are provided, reading every one in detail
is impractical. Use a structured approach:

### Step 1: Stratify by outcome

Split trajectories into three groups:
- **High-reward** (≥ 0.8): the skill working as intended
- **Low-reward** (≤ 0.3): clear failures to analyse
- **Mid-range** (0.3–0.8): partial successes (lower priority, address after
  high and low groups)

Start with low-reward trajectories — they contain the most actionable signal.

### Step 2: Sample representatively

You don't need to read every failure. Sample:
- **5–10 low-reward trajectories** spanning different task types if available
- **3–5 high-reward trajectories** to understand what to preserve
- **2–3 mid-range trajectories** to understand partial failure modes

If trajectories look similar (same tool sequence, same failure point), 3 is
enough — you've already found the pattern.

### Step 3: Cluster failures by root cause

As you read failures, group them by what actually went wrong, not just by
which tool failed. Common root cause clusters:

| Cluster | Signature |
|---|---|
| **Wrong tool selected** | Agent calls tool A when tool B was clearly appropriate |
| **Bad parameters** | Correct tool called, but with invalid/missing/wrong arguments |
| **Missing tool** | Agent improvises a multi-step workaround for something a single tool should do |
| **Wrong sequence** | Tools called in wrong order; result of step N needed before step N-1 |
| **Policy violation** | Agent does something explicitly prohibited |
| **Error not recovered** | First tool error causes agent to abandon the task |
| **Redundant calls** | Same tool called multiple times with same arguments; extra round-trips |

Once you've identified which clusters appear and how often, prioritise by:
- **Frequency × severity**: a failure that occurs in 30% of runs and causes total
  task failure is more important than one that occurs once and costs one extra tool call

### Step 4: Verify a finding appears across multiple trajectories

Before changing anything, confirm that a pattern you see in one trajectory appears
in at least two or three others. Single-trajectory observations may be task-specific
edge cases rather than systematic skill deficiencies.

**Exception**: a single high-severity failure (policy violation, data corruption,
security risk) warrants a fix even if it appears once.

---

## What to Preserve (from High-Reward Trajectories)

Identify patterns that consistently produce successful outcomes:

**Tool sequences that work**
If high-reward runs consistently use a specific tool order (e.g., always validate
before booking, always fetch schema before querying), document that order as an
explicit workflow example or checklist in SKILL.md.

**Parameter patterns that work**
If successful runs consistently pass a parameter in a specific format or within a
specific range, add that as a concrete example in the tool's docstring.

**Recovery strategies that work**
If high-reward runs show the agent retrying with adjusted arguments after a tool
error, document the retry pattern explicitly — don't assume agents will infer it.

**Guardrails that prevented failures**
If a tool consistently returns a clear error when misused, and high-reward runs
respect that, preserve the tool's validation logic and error messages — they are
doing useful work.

---

## What to Fix (from Low-Reward Trajectories)

### Tool selection failures → fix discoverability

If the agent repeatedly picks the wrong tool, the right tool's description is
failing. The agent doesn't recognise it as relevant to the task.

Rewrite the docstring's first line to match the vocabulary and intent of failed
requests. See `05-tool-optimization.md` for discoverability principles.

### Parameter failures → fix usability

If the agent calls the right tool but passes wrong arguments:
- **Wrong type**: add explicit type annotations and docstring type constraints
- **Out-of-range value**: add range constraints in the docstring and input validation in code
- **Missing required field**: mark as non-optional and document in docstring
- **Fabricated parameter name**: add `Literal[...]` type for fixed-value sets; list
  all valid values explicitly in the docstring

### Missing tool → consider a new composite tool

If agents repeatedly string together 3–4 steps to accomplish what should be a
single atomic operation, this is a signal that a composite tool is missing. Define
a new function that wraps the common pattern.

Only add a new tool if the pattern appears across multiple trajectories. Don't
create tools for one-off task variants.

### Wrong sequence → add a workflow snippet

If agents consistently call tools in the wrong order, add an explicit workflow to
SKILL.md:

```markdown
## Order processing workflow

Always follow this sequence — steps have dependencies:
1. `validate_order(order_id)` — must pass before any state changes
2. `reserve_inventory(items)` — locks stock
3. `charge_payment(amount)` — only after inventory confirmed
4. `confirm_order(order_id)` — only after payment succeeds

Do NOT call `charge_payment` before `reserve_inventory` — this causes inventory
conflicts on concurrent orders.
```

### Policy violations → add a guardrail snippet

If agents violate policies, the policy is either absent from the skill or buried
where it won't be seen. Move it to a prominent position in SKILL.md with an
explicit "never do X" statement.

Example:
```markdown
## Policy constraints (read before any tool call)

- NEVER cancel a confirmed order without explicit user confirmation
- NEVER expose customer PII in tool arguments or response text
- NEVER issue a refund above the original order total
```

### Error not recovered → improve error handling guidance

If agents give up on first error, add explicit recovery instructions:

```markdown
If `reserve_inventory` returns InsufficientStockError:
1. Call `check_alternatives(item_id)` to find substitute items
2. Present alternatives to the user before abandoning
Do NOT immediately return an error to the user.
```

### Redundant calls → add an efficiency note

If agents call the same tool multiple times with the same arguments, cache the
result and reference it:

```markdown
Fetch the customer record once at the start of the session and reuse it.
Do not call `get_customer()` more than once per conversation.
```

---

## Translating Trajectory Findings into Skill Changes

| Finding | Where to apply the fix |
|---|---|
| Wrong tool selected | Rewrite tool function docstring first line |
| Agent misuses a parameter | Add constraint to docstring + input validation in code |
| Missing composite tool | Add new Python function in a `.py` file |
| Steps in wrong order | Add numbered workflow checklist to SKILL.md |
| Policy violated | Add prominent policy section to SKILL.md |
| Error handling absent | Add recovery instructions to SKILL.md or tool docstring |
| Redundant tool calls | Add efficiency guidance to SKILL.md |
| Successful pattern lost | Add workflow example or gotcha to SKILL.md |

---

## Prioritising Across Many Findings

After analysing a batch of trajectories, you will have more findings than you
can address in one pass. Prioritise by:

1. **High-frequency failures**: patterns that appear in ≥ 20% of runs
2. **Total task failures**: failures where `reward = 0.0` (not just degraded)
3. **High generality**: failures that occur across many different task types,
   not just one specific scenario
4. **Low fix complexity**: changes that are a one-line docstring update vs. a
   full new tool (quick wins first)
5. **Policy and security violations**: always fix regardless of frequency

Defer low-frequency, case-specific, complex findings — they are edge cases that
may not recur.

---

## Checklist Before Finishing Trajectory-Based Optimization

- [ ] Identified which reward-group (high/low/mid) each trajectory belongs to
- [ ] Sampled at least 5 low-reward and 3 high-reward trajectories
- [ ] Clustered failures by root cause (not just by which tool failed)
- [ ] Verified each finding appears in ≥ 2 trajectories (or is high-severity)
- [ ] Documented at least one successful pattern worth preserving
- [ ] Applied fixes to the highest-frequency, highest-severity failures
- [ ] Did not add tools or snippets based on a single-trajectory observation
- [ ] `required_outputs.json` lists each trajectory-informed change with its rationale

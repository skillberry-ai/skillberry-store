# Skills that bring their tools: rossoctl agents ↔ skillberry-store

rossoctl ships skills to agents, and it ships tools to agents. Today these are two separate wirings, done by hand. [skillberry-store#330](https://github.com/skillberry-ai/skillberry-store/pull/330) joins them **with no change to rossoctl**. This note shows what works now, and what small steps would make it better. Each step is ranked by how little it asks of rossoctl.

## Where we are today

Checked against `rossoctl/rossoctl@1cac9f3f` and `rossoctl/examples@f1fc5df2`.

**Two channels, wired separately:**
- **Skills reach the pod.** A skill registry (skillberry-store, or a local ConfigMap) is synced into the namespace. Linking a skill to an agent adds a `fetch-skill-*` init container that unpacks it to `/app/skills/<name>`, and `SKILL_FOLDERS` says where.
- **Tools reach the agent as MCP endpoints.** That is through `MCP_URL` (one tool, or the MCP Gateway) or `MCP_URLS`, set by hand on the agent. Nothing ties a skill to the tools it relies on.

**What the example agents do with a linked skill:**

| Agent | Reads the skill | Runs its scripts | Tools |
|---|---|---|---|
| `generic_agent` | Puts SKILL.md and every `*.py` into the system prompt (100 KB cap) | No | many, via `MCP_URLS` |
| `weather_service`, `file_organizer`, `image_service`, `reservation_service` | No | No | one `MCP_URL` |
| AG2, CrewAI, Marvin, plain-OpenAI agents | No | No (AG2 sets `code_execution_config=False`) | one `MCP_URL`, or built-in |
| `claude_agent` (not a console preset) | No: `SKILL_FOLDERS` is ignored | **Could:** Claude Code runs with permissions skipped, but is never pointed at the skill | Claude Code's own |

**Not running scripts isn't a security stance.** The docs treat code-running agents as supported:
- the [Sandboxes](https://github.com/rossoctl/rossoctl/blob/main/docs/concepts/experiments/sandboxes.md) page;
- the internal skill-execution e2e;
- AuthBridge, which enforces policy "regardless of the behaviour or the quality of the code of the agent".

It's simply what the example agents do.

## Step 0 — done: the skill and its tools in one agent request (no rossoctl change)

skillberry-store's new `rossoctl-tools` plugin builds on the two channels rossoctl already has. The flow:

1. **Import.** Pick tools that are already deployed in a namespace. The store reads them through rossoctl's existing `/api/v1/tools` API. Each MCP tool becomes a store tool that **references the live tool**: rossoctl tool name, namespace, Service port and MCP tool name.
2. **Compose.** Write the skill around those tools. The store generates a Tools section in SKILL.md, which names each tool by its MCP name and marks which ones change state, plus a `rossoctl-tools.json` that declares the dependency.
3. **Recipe.** For a target namespace, the store checks that every required tool is deployed and ready. It then emits a standard `POST /api/v1/agents` body: `skills: [<skill>]` plus `MCP_URLS`, one `http://<tool>-mcp.<ns>.svc.cluster.local:<port>/mcp` per tool, with the live port. The equivalent `rossoctl agents import` command comes with it.
4. **Deploy.** Send that body to rossoctl, or run the command. rossoctl's existing autosync and init container deliver the skill, and the agent connects to each tool over MCP, through AuthBridge.

On a stock `generic_agent`, the skill supplies the **knowledge**: when to use each tool, and how. The recipe supplies the **connection**. The names match because both come from the same import.

**Demo:** the `night-out-planner` skill gives one `generic_agent` the weather tool and the reservation tool. The agent checks the weather, finds a restaurant, checks availability, confirms with the user and books. Another namespace that lacks a tool is reported before anything is deployed. It runs on **unmodified rossoctl `main`**.

**What step 0 doesn't do:**
- **The wiring happens at create time, outside rossoctl.** rossoctl doesn't know which tools a skill needs. If a tool moves to another port, someone regenerates the recipe.
- **Several tool URLs need an agent that accepts them.** That's `generic_agent`. Single-`MCP_URL` agents use the MCP Gateway, with the tools registered there.
- **Skill scripts don't run on stock agents.** Script-based tools, such as the proxies the store also bundles, help only on agents that run scripts.

## Next steps, ranked by how much they ask of rossoctl

### Step 1 — `rossoctl/examples` only: agents that use the skills they're given

No platform change. Two small changes to agents we already ship:

- **`claude_agent`:** link each `SKILL_FOLDERS` entry into `~/.claude/skills/<name>`, and put `python3` on `PATH`. That's about 30 lines. Claude Code then discovers skills natively, with progressive disclosure, and runs their scripts. Every script-based skill starts working: the summarizer's helpers, eventbridge's CLI, the store's proxies.
- **`generic_agent`:** an opt-in `run_skill_script(skill, script, args)` tool. It runs only files under `<skill>/scripts/`, with no shell, a timeout and an output cap.
- **Docs:** recommend deploying script-running agents as a `Sandbox` workload.

*Why it's worth it:* a skill stops being only text for these agents. A working change exists, ready to propose.

### Step 2 — docs only: say what an agent does with a skill

Add one paragraph to "Bring your own agent". It should say:
- `SKILL_FOLDERS` lists the mounted skills;
- what a skill-aware agent should do with them: read SKILL.md, and optionally run scripts;
- how MCP tools and skills relate.

No code. It gives framework authors a target, and makes step 0's "skill + `MCP_URLS`" a documented pattern rather than a convention.

### Step 3 — a small, flagged backend change: rossoctl wires a skill's tools itself

Only if steps 0–2 prove the pattern. This makes step 0 automatic:
- At agent create, if a linked skill declares its tools, the backend adds their `MCP_URLS` with live Service ports, and warns when a tool is missing. The declaration would be a skill annotation synced from the registry, or a `rossoctl-tools.json` in a local skill.
- It sits behind a feature flag and is off by default. The user's own `envVars` always win.

*Why it's small:*
- it uses no new resource, and needs no operator change;
- it reuses the agent's existing env-var path;
- it's one function at agent create, plus one autosync field.

We have a prototype and are glad to contribute it if there is interest. Until then, the store's recipe covers it.

## Ask

1. **Try step 0.** It needs no rossoctl change. The design and a Kind runbook are in skillberry-store ([`docs/design/rossoctl-skills.md`](https://github.com/erezh16/skillberry-store/blob/rossoctl-skills/docs/design/rossoctl-skills.md), §9A).
2. **Step 1:** would `rossoctl/examples` take the `claude_agent` and `generic_agent` changes as a PR?
3. **Step 3:** is a flagged "wire the skill's tools at agent create" welcome in the backend, or should this stay on the registry side?

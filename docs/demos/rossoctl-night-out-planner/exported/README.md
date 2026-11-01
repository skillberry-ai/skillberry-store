# The exported `night-out-planner` skill (reference copy)

This is the package rossoctl's skill-fetch init container unpacked into the agent pod
(`/app/skills/night-out-planner`) during the demo run. It is exactly what
`GET /skills/night-out-planner/export-anthropic` returns. The store generates it on every export;
this copy is kept here only so the result can be read without running the demo.

| File | What it is | Who uses it on a stock rossoctl agent |
|---|---|---|
| `SKILL.md` | The author's procedure, plus a generated **Tools** section that names each rossoctl tool by its **MCP tool name** | `generic_agent` puts it in its system prompt |
| `rossoctl-tools.json` | The tools the skill depends on, with ports and MCP tool names | the store's `/recipe` and `/check`, and people |
| `scripts/*.py` | One proxy per MCP tool (a store code tool's module) | not used by stock agents. Agents that run scripts can use them. |

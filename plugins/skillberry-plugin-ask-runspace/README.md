# Skillberry "Ask Runspace" Plugin

Run the **Runspace agent** on a free-text task — optionally seeded by an example
preset — then render the agent's `summary.md` back to you as Markdown.

## How it works

- **Run task** takes a free-text `request` — that text **is** the whole prompt sent to
  the agent (no server-side composition). The UI offers an **example dropdown** that, on
  selection, prefills the request textarea with a starter prompt and prefills the
  **skills** list; both stay fully editable. Examples include "Create a tool that…",
  "Create a skill that…", "Optimize a skill…", "Research and summarize…", "Write
  documentation for…", "Debug / fix…", and a generic "Anything — describe the task
  yourself". They're advertised at `GET /plugins/ask-runspace/presets` (each returns
  `id`, `label`, `prompt`, `skills`).
- **Skills**: the optional `skills` list is a set of remote skill sources loaded into the
  agent via `npx skills add` (runspace `remote_skills`) — GitHub URLs or `owner/repo`.
  Selecting an example fills these in (e.g. the skill-creator or evo-graph repos); you can
  add or remove sources before running.
- The plugin spins up a Runspace agent session (with fresh `editable` and `context`
  working directories), installs any `skills`, runs the agent on your `request`, and waits.
- **Async + status**: `POST /plugins/ask-runspace/run` returns a `job_id` immediately.
  Poll `GET /plugins/ask-runspace/status/{job_id}` for `pending` → `ready` / `failed`.
  When `ready`, the response includes `session_id` and `summary_md` (and, when skills were
  loaded, a `Loaded skills: …` message).
- **Summary**: the agent's `summary.md` is read and rendered as Markdown in the UI (a short
  notice is shown if the agent produced none).
- **Workspace**: by default the scratch workspace is deleted after the run. Tick **Keep
  workspace folder** to retain it; the result then offers a **Delete workspace** button.

## Installation

```bash
uv pip install -e ".[plugin-ask-runspace]"
```

This requires the `runspace-agent` dependency to be importable; if it is missing the
plugin reports `Missing dependency: runspace-agent not installed` and stays disabled.

## Credentials

Credentials for the Claude Code agent are resolved by the shared
`skillberry_store.plugins.claude_credentials` helper, in increasing priority:

1. The `env` block of `~/.claude/settings.json`.
2. Process environment variables (`ANTHROPIC_*` / `CLAUDE_*`).
3. Per-run `agent_env` overrides passed with the request.

The plugin is considered configured when either:

- `ANTHROPIC_API_KEY` is set, **or**
- both `ANTHROPIC_BASE_URL` and `ANTHROPIC_AUTH_TOKEN` are set (gateway-style access).

If neither is present the plugin reports a missing-credentials status and stays
disabled.

## Configuration

See `.env.example`.

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | one of these | — | Direct Anthropic API key |
| `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN` | one of these | — | Gateway base URL + auth token (alternative to the API key) |
| `RUNSPACE_MODE` | no | `container` | Agent execution mode: `container` or `local` |

`RUNSPACE_MODE` sets the default execution mode for the agent session; it can be
overridden per request via the `execution_mode` field (`container` / `local`).

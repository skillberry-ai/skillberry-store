# Skillberry "Ask Runspace" Plugin

Run the **Runspace agent** on a free-text task — optionally seeded by an example
preset — then render the agent's `summary.md` back to you as Markdown.

## How it works

- **Run task** takes a free-text `request` describing what you want done. You may
  optionally pick a `preset_id` (e.g. "Create a tool that…", "Create a skill that…",
  "Research and summarize…", "Refactor / improve…"); the preset's guidance is
  prepended to your request to seed the prompt. Presets are advertised at
  `GET /plugins/ask-runspace/presets` and surface as a dropdown in the UI.
- The plugin spins up a Runspace agent session (with fresh `editable` and `context`
  working directories), runs the agent against the composed prompt, and waits for it
  to finish.
- **Async + status**: `POST /plugins/ask-runspace/run` returns a `job_id` immediately.
  Poll `GET /plugins/ask-runspace/status/{job_id}` for `pending` → `ready` / `failed`.
  When `ready`, the response includes `session_id` and `summary_md`.
- **Summary**: when the agent produces a `summary.md`, the plugin reads it and the UI
  renders it as Markdown.

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

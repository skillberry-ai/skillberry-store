# Plugin Installation Guide

## Overview

Skillberry Store hosts plugins as **out-of-process subprocesses**. On boot, SBS starts with **zero plugins installed**. Plugins live under [plugins/](../plugins/) as installable Python packages; each is registered on demand through the SBS API and runs in its own venv on `127.0.0.1:<port>`, reached via the reverse proxy at `/plugins/{slug}/…`.

Architecture and rationale: see [plugin-separation-plan.md](plugin-separation-plan.md); execution stages and gates: see [plugin-process-migration-plan.md](plugin-process-migration-plan.md).

## Installing a plugin

There are two supported entry points: the UI dialog and the REST API.

### From the UI

1. Open the **Plugins** page.
2. Click **Install plugin…** in the toolbar.
3. Select one or more entries from the catalog. For each selection, fill in any required env vars listed in the dialog.
4. Click **Install** — SBS creates a per-plugin venv, `pip install`s the plugin editable from `plugins/<slug>/`, records the state, and starts the subprocess.

### From the API

```bash
# List available plugins
curl http://localhost:8000/plugins/available

# Install (autostart=true is the default; env overrides live in the body)
curl -X POST 'http://localhost:8000/plugins/kagenti-approver/install?autostart=true' \
     -H 'Content-Type: application/json' \
     -d '{"env_overrides": {}}'

# Inspect state (state ∈ installed | starting | running | stopping | error)
curl http://localhost:8000/plugins/kagenti-approver

# Lifecycle controls
curl -X POST http://localhost:8000/plugins/kagenti-approver/stop
curl -X POST http://localhost:8000/plugins/kagenti-approver/start
curl -X POST http://localhost:8000/plugins/kagenti-approver/restart

# Uninstall (removes venv and state entry)
curl -X DELETE http://localhost:8000/plugins/kagenti-approver
```

Missing required env vars are surfaced as HTTP `422` with a structured body:

```json
{ "error": "missing_env", "missing": ["LLM_PROVIDER"], "slug": "creator" }
```

### Env-var reference (plugins that require them)

- **evaluator, security, dedupe, doc-generator, creator, skill-optimizer** — `LLM_PROVIDER` (required), `LLM_MODEL` (optional; defaults to `gpt-4`).
- **anthropic-skill-generator** — one of `ANTHROPIC_API_KEY` or a proxy set (`ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN`). Optional `ANTHROPIC_MODEL`, `RUNSPACE_MODE` (`container` default), `RUNSPACE_MAX_TURNS`.
- **simulate** — Docker socket. If missing, the plugin still starts but `/lifecycle/ready` reports `missing_config: ["docker socket"]`.
- **kagenti-approver** — optional `KAGENTI_CRITERIA` (see below).

## Persistence

Every install/uninstall is recorded in `plugins.state.json` at the repo root (or wherever `SKILLBERRY_PLUGIN_STATE_FILE` points). Each entry has:

```json
{
  "installed_at": "2026-07-05T09:00:00Z",
  "autostart": true,
  "env_overrides": {},
  "last_state": "running"
}
```

On next SBS boot, every entry with `autostart: true` is started in the background. Failures land in `last_state = "error"` and don't block startup.

Setting `SKILLBERRY_PLUGIN_STATE_FILE=""` (empty string) tells SBS to boot with no plugins persisted — this is how the pytest suite runs.

## Events

Plugins receive content-change events via a shared SSE stream:

```
GET /events/stream?topics=content.skill.*,content.tool.added
Authorization: Bearer <plugin-token>
Last-Event-ID: <opaque>          # optional, for resume after disconnect
```

Topics use dot-segment wildcards: `content.<type>.<action>` where `type ∈ skill|tool|snippet` and `action ∈ added|updated|deleted`. `*` matches one segment, `**` matches many.

## Writing a new plugin

Each plugin is a Python package that depends on `skillberry-plugin-sdk`:

```
plugins/skillberry-plugin-<slug>/
├── manifest.yaml
├── pyproject.toml
├── src/skillberry_plugin_<slug>/
│   ├── __init__.py
│   ├── __main__.py       # calls run(YourPlugin)
│   ├── manifest.yaml     # same content — packaged with the wheel
│   └── plugin.py
└── tests/
```

Minimal `plugin.py`:

```python
from skillberry_plugin_sdk import PluginLifecycleBase, on_event

class MyPlugin(PluginLifecycleBase):
    manifest_path = "manifest.yaml"

    async def on_start(self):
        # optional: build clients here
        pass

    @on_event("content.skill.added")
    async def handle_new_skill(self, event):
        uuid = event.data["uuid"]
        skill = await self.store.get_skill(uuid)
        # do something...
```

`manifest.yaml`:

```yaml
name: My Plugin
slug: my-plugin
version: 0.1.0
description: What this plugin does
plugin_type: evaluator
sdk_version: ^0.1
has_api: false
required_env:
  - name: MY_TOKEN
    required: true
```

`__main__.py`:

```python
from skillberry_plugin_sdk import run
from skillberry_plugin_my_plugin.plugin import MyPlugin

if __name__ == "__main__":
    run(MyPlugin)
```

`pyproject.toml` should depend on `skillberry-plugin-sdk` and declare `manifest.yaml` as `package-data`.

## Kagenti Approver criteria

`kagenti-approver` still reads `KAGENTI_CRITERIA` from the env; syntax:

- `,` = AND, `|` = OR, operators: `>=`, `>`, `<=`, `<`, `=`, `!=`
- Each condition: `<score-tag><op><number>` (e.g. `security-score>=9`)

Default: `security-score>=7`.

## Troubleshooting

**Plugin lands in `error` state with `missing_env` in the detail** — populate the missing vars via env or install-time `env_overrides`, then call `POST /plugins/<slug>/restart`.

**Plugin state file is corrupt** — SBS logs a warning at boot and starts empty. Delete the file to reset.

**Plugin port collision** — SBS allocates from `8100-8200`. If the whole range is full, `start` returns `HTTP 500`.

## Support

- Issues: https://github.com/skillberry-ai/skillberry-store/issues
- Docs: [docs/](.)
- Example plugin: `plugins/skillberry-plugin-kagenti-approver/`

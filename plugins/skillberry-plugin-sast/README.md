# Skillberry Plugin: SAST

Static Application Security Testing for Skillberry Store. Scans the **code** of
tools, skills, and snippets with open-source SAST engines and records concrete,
line-level findings.

## How this differs from `skillberry-plugin-security`

| | `skillberry-plugin-security` | `skillberry-plugin-sast` (this) |
|---|---|---|
| Method | LLM judges "security posture" | Real static-analysis engines (Bandit) |
| Output | One 1–10 score + prose | List of findings: rule, severity, line |
| LLM required | Yes | No — offline & deterministic |
| Reproducible | No | Yes |

They are complementary; this plugin does not replace or modify the LLM one.

## Flag-only

Findings are written back as tags and into `extra["evaluation"]["sast"]`. The
plugin **never blocks or rejects** content — the store has no such mechanism.

## Engines

Multi-engine by design. **Bandit** (Python) ships now; more engines (e.g.
Semgrep) can be added to the registry without restructuring.

Install the engine(s) you want as extras:

```bash
pip install -e 'plugins/skillberry-plugin-sast[bandit]'
```

### Selecting engines

Two comma-separated env vars control engines:

- **`SBS_SAST_AVAILABLE_ENGINES`** — the engines *offered* (the dropdown set),
  intersected with what's actually implemented; unknown names are ignored.
  Unset ⇒ all implemented engines. Today only **bandit** is implemented.
- **`SBS_SAST_ACTIVE_ENGINES`** — the engines *active* by default (pre-selected
  in the UI and used by auto-scan-on-ingest). Constrained to the available set;
  defaults to **bandit**.

In the UI, the **Scan code (SAST)** action shows an engines **multi-select
dropdown** populated from the available set with the active set pre-selected —
per-request overrides come from there (no free-text).

A requested engine that is unknown or not installed is **skipped and reported**
per-engine (e.g. `"status": "not_installed"`); the scan still runs the engines
that are available. The plugin is enabled when at least one active engine is
installed.

## What it scans

- **Tools:** the module source file (`programming_language` selects the engine).
- **Snippets:** inline content.
- **Skills:** no own code — selecting a skill scans its referenced tools and
  snippets (the same fan-out used by auto-scan on ingest).

The object's type is **inferred from its UUID** — callers pass UUIDs, not types.
Bandit covers Python today; non-Python blobs are reported as
`language_unsupported`.

## Scanning

`POST /api/plugins/sast/scan` takes one or more object UUIDs (skills/tools/
snippets); the type of each is inferred:

```json
{ "object_uuids": ["<uuid>", "<uuid>"], "engines": ["bandit"] }
```

In the UI, the **Scan code (SAST)** action shows a searchable multi-select
browser of skills/tools/snippets — no UUID typing or type selection needed.

Response:

```json
{
  "success": true,
  "results": [
    {
      "uuid": "…",
      "content_type": "tool",
      "engines": {
        "bandit": {"status": "ok", "findings": [
          {"engine": "bandit", "rule_id": "B602", "severity": "high",
           "message": "subprocess call with shell=True identified…",
           "line": 12, "snippet": "…", "file": "tool.py"}
        ]},
        "semgrep": {"status": "not_installed"}
      },
      "summary": {"low": 0, "medium": 0, "high": 1, "critical": 0},
      "findings": [ … ]
    }
  ],
  "not_found": [],
  "summary": {"low": 0, "medium": 0, "high": 1, "critical": 0}
}
```

UUIDs that resolve to nothing are reported in `not_found` rather than failing the
whole batch. For tools and snippets the findings are persisted to
`extra["evaluation"]["sast"]` and summarized as tags (`sast:high:1`, or
`sast:clean`).

In the UI report you can **filter findings by severity** (low/medium/high/
critical chips) and **select objects** to fix.

## Fixing (LLM, optional)

The report's **Fix** button asks an LLM to rewrite the offending code. It is
**disabled unless an LLM key is configured** — install the extra and set the
provider/key:

```bash
pip install -e 'plugins/skillberry-plugin-sast[bandit,llm]'
export LLM_PROVIDER=openai.async   # default
export LLM_MODEL=gpt-4             # target model
export OPENAI_API_KEY=sk-...       # required
```

`GET /plugins/sast` reports `ui_config.capabilities.fix` so the UI knows whether
to enable the button.

`POST /api/plugins/sast/fix` takes the selected object UUIDs and the severities
to address:

```json
{ "object_uuids": ["<uuid>"], "severities": ["high", "critical"] }
```

For each object the plugin re-scans, filters findings to the requested
severities, sends them plus the source to the model, and **overwrites the code
in place** (tool module file / snippet content). The fix is recorded under
`extra["evaluation"]["sast_fix"]` (model, severities, rule_ids) without
clobbering the `sast` findings block. The response returns `old_code`/`new_code`
per object so the UI can show the diff; re-scan to confirm the findings cleared.
Skills (no own code) are skipped.

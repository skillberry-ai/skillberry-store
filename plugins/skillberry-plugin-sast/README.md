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

- **Per request:** `POST /api/plugins/sast/scan` with
  `{"uuid": "...", "content_type": "tool", "engines": ["bandit"]}`.
  Multiple engines may be selected.
- **Default:** when `engines` is omitted (and for auto-scan on ingest), the
  comma-separated `SBS_SAST_ENGINES` env var is used (default: `bandit`).

A requested engine that is unknown or not installed is **skipped and reported**
per-engine (e.g. `"status": "not_installed"`); the scan still runs the engines
that are available. The plugin is enabled when at least one configured engine is
installed.

## What it scans

- **Tools:** the module source file (`programming_language` selects the engine).
- **Snippets:** inline content.
- **Skills:** no own code — scans referenced tools/snippets (auto-scan fans out).

Bandit covers Python today; non-Python blobs are reported as
`language_unsupported`.

## Output

`POST /api/plugins/sast/scan` →

```json
{
  "success": true,
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
```

For tools and snippets the same data is persisted to
`extra["evaluation"]["sast"]` and summarized as tags (`sast:high:1`, or
`sast:clean`).

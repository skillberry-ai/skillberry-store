# skillberry-plugin-dependency-tracker

**Dependency Tracker** — discovers the **external dependencies** of skills, tools,
and snippets and records them under a hierarchical `extra["dependencies"]` block.
Addresses [#224](https://github.com/skillberry-ai/skillberry-store/issues/224).

The store already tracks **internal** dependencies (a tool's dependency on *other
store tools*, by UUID, in the top-level `dependencies` field). This plugin tracks
the **external supply chain** — the packages/commands an object actually pulls in,
their transitive deps, exact versions, and hashes — which matters for supply-chain
security and versioning hygiene.

## Supported languages

| Language | What's discovered | Version / hash |
|----------|-------------------|----------------|
| **Python** | imported PyPI distributions, transitive at **maximum depth** | installed version + RECORD hashes (local), canonical sha256 (PyPI) |
| **Shell** (`.sh`/`.bash`/…) | external commands invoked (`curl`, `jq`, `node`, …) | none — these are *system* executables (`source: "system"`) |

Each file's language is detected by extension, then shebang, then a light content
heuristic. **Any file in an unsupported language is reported explicitly** in
`skipped_files` (with `reason: "unsupported_language"`) and counted in
`summary.skipped_count` — a bare `0` is never ambiguous about whether the object
was clean or simply not inspectable.

## Resolution (hybrid)

| Source | Role |
|--------|------|
| **Local** (`importlib.metadata`) | **Source of truth** — the installed version each object runs against, per-file `RECORD` hashes, and the transitive `Requires-Dist` graph at max depth |
| **PyPI** (`/pypi/<pkg>/json`) | **Best-effort enrichment** — canonical published artifact `sha256` + an "update available" signal |

PyPI calls are **time-boxed and never fail a scan**: a 429 / timeout / offline
condition becomes a per-package `status`, rolled up to `partial` / `skipped`.
Enrichment is env-gated: `DEPENDENCY_TRACKER_PYPI=off` disables it (and a `pypi`
flag on the request overrides per call).

## The `extra["dependencies"]` block

```jsonc
{
  "schema_version": 1,
  "generated_at": "<ISO-8601>",
  "supported_languages": ["python", "shell"],
  "languages_inspected": ["python", "shell"],   // which langs this object had
  "scanner": { "plugin_version", "resolver": "hybrid", "python_version" },
  "summary": { "direct_count", "total_count", "unresolved_count",
               "skipped_count", "update_available_count", "pypi_status" },
  "packages": {                          // keyed by dependency name
    "requests": {
      "name", "version",                 // local installed version = truth
      "source": "local|pypi|system|unresolved",
      "language": "python",
      "direct": true, "depth": 0,
      "local_hashes": [ {"file","algorithm":"sha256","hash"} ],
      "requires": ["urllib3", ...],
      "pypi": { "status", "latest_version", "update_available",
                "artifact_sha256": {"sdist","wheel"} }
    },
    "curl": { "name": "curl", "version": null, "source": "system",
              "language": "shell", "direct": true, "depth": 0 }
  },
  "tree": [ {"from","to","depth"} ],     // dependency edges (DAG/cycle-safe)
  "unresolved_imports": [ {"import_name","reason"} ],
  "skipped_files": [ {"file","language","reason":"unsupported_language"} ]
}
```

Summary tags are also written: `dep:count:N`, `dep:unresolved:M`,
`dep:skipped:K` (unsupported files), `dep:lang:python` / `dep:lang:shell`, and
`dep:update-available` when any package has a newer release.

## API

Mounted at `/plugins/dependency_tracker` (and `/api/plugins/dependency_tracker/...` for the UI):

- `POST /resolve-dependencies` — body `{ "object_type": "skill|tool|snippet", "uuid": str, "pypi"?: bool }`
  → `{ success, message, data: { object_type, uuid, dependencies, summary } }`

Invalid/missing input returns a clean **400** (not a raw 422). **On-demand only** —
there is no auto-scan-on-import hook.

## UI

No custom UI: the plugin declares a single **"Scan dependencies"** action via
`get_ui_config()`, rendered by the store's generic plugin action form (mirrors the
SAST/provenance plugins).

## Install

```bash
pip install -e plugins/skillberry-plugin-dependency-tracker
# optional: robust PEP 440 version comparison
pip install -e 'plugins/skillberry-plugin-dependency-tracker[version]'
```

## Test

```bash
pytest plugins/skillberry-plugin-dependency-tracker/tests -q
```

Tests are network-free: PyPI is monkeypatched and local resolution runs against
the installed environment.

## Notes

- **Non-destructive**: only `extra["dependencies"]` and `dep:` tags are written;
  other `extra` keys and tags are preserved. The top-level store-tool
  `dependencies` field is never touched.
- **Maximum depth**: the transitive graph is walked fully, with cycle/diamond
  protection (each distribution expanded once; shallowest depth recorded).
- Distributions with no recorded `RECORD` hashes (editable installs, some wheels)
  still get a version + `source: local`, just with empty `local_hashes`.
- Imports that map to no installed distribution are reported in
  `unresolved_imports`, never silently dropped.

# skillberry-plugin-provenance

**Skill Provenance & Background** — gathers and displays the trust "background"
of a skill so a user importing it (or auditing it later) has a basis for
confidence. Addresses [#197](https://github.com/skillberry-ai/skillberry-store/issues/197).

It answers five questions, the "top 5" pieces of background information:

| # | Section      | Question                                   | Source |
|---|--------------|--------------------------------------------|--------|
| 1 | `provenance` | Where did it come from? (repo/ref/path pinned to a commit SHA) | GitHub API |
| 2 | `publisher`  | Who published it, and is the source reputable? | GitHub API |
| 3 | `license`    | Is it legally safe to use / redistribute?  | GitHub API |
| 4 | `integrity`  | Is this the genuine, unmodified artifact?  | GitHub commit verification + local content hash |
| 5 | `behavior`   | What does it reach out to or run?          | static pass over stored files + any SAST result |

These roll up into a single `confidence` of **high / medium / low** with
human-readable reasons.

## Modes

- **Pre-import** — call with a `github_url`; nothing needs to be stored yet.
- **Post-import** — call with a skill `uuid`; origin is read from the skill's
  `extra["origin"]` (captured at import time for GitHub URL imports).
- **Drift / re-check** — `recheck` re-gathers and diffs against the baseline
  stored in `extra["provenance"].baseline`, reporting what changed
  (e.g. license, commit SHA, stars, archived).

When a skill is imported from a GitHub URL, the plugin computes the background
automatically on the `content_added:skill` event and stores it as the baseline.

## API

Mounted at `/plugins/provenance` by the store:

- `POST /check`   — body `{ "github_url"?: str, "uuid"?: str }` → `{ success, message, data }`
- `POST /recheck` — body `{ "uuid": str }` → `{ success, message, data: { drift, current, baseline } }`

The store also exposes these under `/api/plugins/provenance/...` for the UI.

## UI

No custom UI: the plugin declares a single action via `get_ui_config()`, which
the store's generic plugin action form renders (two optional text inputs, and a
JSON view of the returned background). This mirrors the SAST plugin.

## Install

```bash
pip install -e plugins/skillberry-plugin-provenance
```

## Test

```bash
pytest plugins/skillberry-plugin-provenance/tests -q
```

Tests are network-free: the GitHub mapping is exercised against captured JSON
fixtures, and the plugin is exercised with a fake source and a mocked store.

## Notes

- Network calls are best-effort and time-boxed (30s); a rate-limited or failed
  call degrades that section's `status` rather than failing the whole gather or
  blocking an import.
- This plugin is **informational** — it does not block or gate imports.
- Auth for GitHub calls reuses the store's per-endpoint resolver
  (`skillberry_store.tools.endpoint_auth.resolve_auth_headers`), so a configured
  token or the `gh` CLI credentials are used automatically when present.

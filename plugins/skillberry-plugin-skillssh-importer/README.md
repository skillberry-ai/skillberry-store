# skillberry-plugin-skillssh-importer

Skillberry Store plugin for searching and importing skills from the
[skills.sh](https://www.skills.sh) directory.

## What it does

1. **Search** — query the skills.sh catalogue (fuzzy for single words,
   semantic for multi-word queries) and browse results with install counts.
2. **Select** — pick one or more skills by their `id` from the search results.
3. **Import** — fetch each skill's files (including `SKILL.md`), run them
   through the existing Anthropic skill importer pipeline, and persist the
   resulting tools, snippets, and skill in the store.
4. **Tag automatically** — every imported item receives:
   - `skills.sh` — source marker
   - `installs:<bucket>` — e.g. `installs:10k+`, `installs:1k+`, …
   - `audit:<provider>:<status>` — one per security audit partner
     (Socket, Snyk, Gen Agent Trust Hub, Runlayer, ZeroLeaks)
   - `audit:pass` / `audit:warn` / `audit:fail` — overall worst-case summary

---

## Authentication

skills.sh requires a **Vercel OIDC token** for every API call (including
search). There is no unauthenticated tier and no separate API key sign-up.

The plugin tries three sources in order, automatically and silently:

| Priority | Source | Notes |
|---|---|---|
| 1 | `skills_sh_token` request field | Per-call override; useful for testing |
| 2 | `SKILLS_SH_TOKEN` env var | Checked on every call; JWT expiry decoded |
| 3 | Vercel CLI credentials | Automatic mint + refresh via `@vercel/oidc` |

### Option A — environment variable (quickest)

Obtain a token by linking your project to Vercel once and pulling env vars:

```bash
npm install -g vercel
vercel link          # one-time: links this directory to a Vercel project
vercel env pull      # writes VERCEL_OIDC_TOKEN into .env.local (~12 h)
```

Then export it before starting the store:

```bash
export SKILLS_SH_TOKEN=$(grep VERCEL_OIDC_TOKEN .env.local | cut -d= -f2)
```

> The token is valid for ~12 hours. Re-run `vercel env pull` when it expires,
> or use Option B for zero-maintenance operation.

### Option B — automatic via Vercel CLI (recommended, zero maintenance)

Run these commands **once** in the project root:

```bash
npm install -g vercel
vercel login         # stores long-lived OAuth credentials in ~/.local/share/com.vercel.cli/
vercel link          # writes .vercel/project.json with your projectId + teamId
```

After that, **no env var is needed**. Every time the plugin makes an API call:

1. It checks whether the current token (env var or in-process cache) is still
   fresh (reads the JWT `exp` claim without signature verification).
2. If missing or expiring within 60 seconds it spawns a Node subprocess:
   ```
   node -e "require('@vercel/oidc').getVercelOidcToken().then(…)"
   ```
3. `@vercel/oidc` exchanges the stored CLI credentials for a new OIDC JWT via
   `POST https://api.vercel.com/v1/projects/{projectId}/token`.
4. The fresh token is cached in-process and written back to `SKILLS_SH_TOKEN`
   so subsequent calls within the same process skip the Node spawn.
5. On a `401` response the cache is invalidated and the cycle repeats once.

Node.js (any recent version) must be on `PATH` for Option B to work.
`@vercel/oidc` is automatically available when installed via `npm i @vercel/oidc`
in the workspace.

---

## Plugin status in the UI

| State | `enabled` | `status` message |
|---|---|---|
| `SKILLS_SH_TOKEN` set | `true` | `Ready — token from SKILLS_SH_TOKEN env var` |
| `.vercel/project.json` found | `true` | `Ready — token will be auto-acquired via Vercel CLI` |
| Neither | `false` | `Disabled: no token source configured. Option A … Option B …` |

When disabled, the plugin card in the UI turns grey, actions are hidden, and
`setup_instructions` (title, two setup steps with descriptions, and a link to
the skills.sh API docs) is surfaced so the user sees exactly what to do.

---

## Endpoints

Both endpoints are mounted at `/plugins/skillssh-importer/`.

### `POST /search`

Search the skills.sh catalogue.

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `query` | string | ✓ | — | Search query (≥ 2 chars). Single-word → fuzzy, multi-word → semantic. |
| `limit` | integer | | 50 | Max results (1–200) |
| `owner` | string | | — | Restrict to a GitHub owner (e.g. `"vercel-labs"`) |
| `skills_sh_token` | string | | — | Override token for this request |

Returns `{ "success": true, "data": { "items": [...], "count": N, "query": "..." } }`.
Each item follows the generic `CatalogItem` contract the core UI's catalog-import
renderer consumes — `id`, `title`, `subtitle`, `source`, `description` (lazily
filled by `/skill-description`), `details` (popover rows: `{label, value, href?}`),
and `badges`. skills.sh-specific fields (`sourceType`, `installUrl`, `isDuplicate`,
install counts) are folded into `details`/`badges` by the plugin, so no skills.sh
field names leak into the core UI. Pass the `id` values to `/import`.

### `POST /import`

Import one or more skills from skills.sh into the store.

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `skill_ids` | string[] | ✓ | — | IDs from search results, e.g. `["vercel-labs/skills/find-skills"]` |
| `tags` | string[] | | `[]` | Extra tags added to all imported tools, snippets, and skills |
| `fetch_audits` | boolean | | `true` | Fetch security audit results and attach as tags |
| `skills_sh_token` | string | | — | Override token for this request |

Returns (the `data.imported` items carry the generic `id`/`title`/`summary` fields
the core UI renders, plus structured fields for programmatic callers; `data.failed`
items are `{ id, error }`):
```json
{
  "success": true,
  "message": "Imported 1 skill successfully",
  "data": {
    "imported": [
      {
        "id": "vercel-labs/skills/find-skills",
        "title": "find-skills",
        "summary": "2 tools, 1 snippet",
        "skill_uuid": "...",
        "tools_imported": 2,
        "snippets_imported": 1,
        "tags": ["skills.sh", "installs:10k+", "audit:socket:pass", "audit:pass"],
        "installs": 24531,
        "audits": [{ "slug": "socket", "status": "pass", "summary": "No alerts", ... }]
      }
    ],
    "failed": []
  }
}
```

---

## Installation

```bash
pip install -e plugins/skillberry-plugin-skillssh-importer
```

The plugin registers itself via the `skillberry_store.plugins` entry-point and
is discovered automatically when the store starts.

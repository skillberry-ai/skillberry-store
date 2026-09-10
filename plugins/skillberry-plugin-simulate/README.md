# Skillberry "Simulate This" Plugin

Stand up a **simulated parallel vMCP** for a skill — a second vMCP whose tools are
backed by a containerized [simulation-harness](https://github.com/skillberry-ai/simulation-harness)
instead of the real backends — and flip a plugin-owned switch deciding whether
consumers reach the real or the simulated vMCP.

## How it works

- **Simulate this** takes a `skill_uuid` as its primary input. If the skill has exactly one
  non-simulation vMCP that is the target; if it has multiple, pass `vmcp_uuid` to specify
  which is "real". The plugin builds a simulation skill + simulated tool manifests
  (MCP-packaged, pointing at the harness), creates a parallel vMCP referencing them, launches
  the harness container, and records the real/sim pair in a registry (`active="real"`).
  If a simulation already exists for the skill it is torn down automatically before the new
  one is created — re-simulating is always safe. Passing a simulation-tagged vMCP UUID as
  `vmcp_uuid` is rejected with an error.
- **Toggle real/sim** flips the active vMCP for a skill. It takes effect on the consumer's
  **next** resolve+connect — there is no mid-session redirection (between-runs contract).
- **Resolve**: consumers call `GET /plugins/simulate/active/{skill_uuid}` at the start of
  each use and connect to the returned `mcp_url`. The response includes `mode` (`real`/`sim`).
- **Tear down** deletes the sim vMCP, its tools and skill, stops the harness, and reverts.

## The harness

The harness is [`skillberry-ai/simulation-harness`](https://github.com/skillberry-ai/simulation-harness),
published to `ghcr.io/skillberry-ai/simulation-harness` (public — no registry
login needed). The plugin drives its REST control plane on container port `8086`
(`POST`/`GET`/`DELETE /api/v1/simulation`) and passes a dedicated `mcp_port`, so
each simulation's MCP server runs on its own port as a sidecar. The harness
returns that sidecar's SSE URL (`http://127.0.0.1:<mcp_port>/mcp/sse`), which is
what the simulated tool manifests point at.

**Image tag.** The default is `:0.1` — the newest `v0.1.x` *release*. Do not use
`:latest`: upstream tags that from every push to `main`, so it runs ahead of any
release and can change the REST contract between runs. The plugin's contract is
verified against v0.1.2; a `v0.2.0` release will need a deliberate bump here.

## Configuration

See `.env.example`. Requires `SIMULATE_LLM_API_KEY` and a reachable Docker runtime.

| Variable | Required | Default | Description |
|---|---|---|---|
| `SIMULATE_LLM_API_KEY` | yes | — | API key for the harness simulation LLM |
| `SIMULATE_LLM_API_BASE` | no | — | Azure/OpenAI-compatible base URL |
| `SIMULATION_HARNESS_IMAGE` | no | `ghcr.io/skillberry-ai/simulation-harness:0.1` | Container image to launch |
| `SIMULATE_LLM_PROVIDER` | no | — | Harness `HARNESS_LLM_PROVIDER` override |
| `SIMULATE_LLM_SKILL_GENERATION_MODEL` | no | — | Harness `HARNESS_LLM_SKILL_GENERATION_MODEL` override |
| `SIMULATE_LLM_SIMULATION_MODEL` | no | — | Harness `HARNESS_LLM_SIMULATION_MODEL` override |
| `SIMULATE_DATA_DIR` | no | `~/.skillberry/simulate` | Path for the active-vMCP registry |
| `SIMULATE_SKILLS_STORE_PATH` | no | — | Host path bind-mounted at `/app/skills-store` (**read-write**) |
| `SIMULATE_LOGS_PATH` | no | — | Host path bind-mounted at `/app/logs` |
| `SIMULATE_READY_TIMEOUT_SECONDS` | no | `600` | Seconds to wait for harness to become ready |

The harness image ships a `harness.yaml` defaulting to provider `openai` with
`gpt-4.1` for both its skill-generation and simulation models. If
`SIMULATE_LLM_API_BASE` points at a gateway that namespaces model ids
differently, set the three `SIMULATE_LLM_*_MODEL` / `_PROVIDER` variables;
unset means "leave the image's defaults alone".

### Generated-skill cache

The harness generates a skill (`SKILL.md`, `schema.json`, `db.json`, `api.json`)
from the synthesized OpenAPI spec and caches it under
`<skills-store>/<simulation name>/`, skipping the (slow, LLM-driven) generation
on a cache hit. Every simulation shares whatever `SIMULATE_SKILLS_STORE_PATH`
points at, so the plugin names each simulation `<skill-slug>-<tools-fingerprint>`:
unique per skill *and* per tool surface, so same-named skills never collide and
changing a skill's tools regenerates rather than silently reusing stale
artifacts. This mount must be read-write or generation fails.

## Limitations (v1)

- Whole-surface switch (the whole skill flips together), not per-tool.
- Between-runs switching only (no mid-session real↔sim redirection).
- Response fidelity is bounded by input-schema-only OpenAPI synthesis; the synthesizer is
  pluggable for a future "enhanced" generator.
- Harness session limits (≈100 messages, ~1h idle, queue depth 8) apply, so simulated
  throughput is lower than the real backend. The **harness** resets its own session on
  expiry and fails just the one call that tripped the limit; the plugin is not in the
  tool-call path and neither sees nor handles this.

# Skillberry "Simulate This" Plugin

Stand up a **simulated parallel vMCP** for a skill — a second vMCP whose tools are
backed by a containerized simulation-harness instead of the real backends — and flip a
plugin-owned switch deciding whether consumers reach the real or the simulated vMCP.

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

## Configuration

See `.env.example`. Requires `SIMULATE_LLM_API_KEY` and a reachable Docker runtime.

| Variable | Required | Default | Description |
|---|---|---|---|
| `SIMULATE_LLM_API_KEY` | yes | — | API key for the harness simulation LLM |
| `SIMULATE_LLM_API_BASE` | no | — | Azure/OpenAI-compatible base URL |
| `SIMULATION_HARNESS_IMAGE` | no | `simulation-harness:latest` | Container image to launch |
| `SIMULATE_DATA_DIR` | no | `~/.skillberry/simulate` | Path for the active-vMCP registry |
| `SIMULATE_SKILLS_STORE_PATH` | no | — | Host path mounted into the harness |
| `SIMULATE_LOGS_PATH` | no | — | Host path mounted into the harness |
| `SIMULATE_READY_TIMEOUT_SECONDS` | no | `600` | Seconds to wait for harness to become ready |

## Limitations (v1)

- Whole-surface switch (the whole skill flips together), not per-tool.
- Between-runs switching only (no mid-session real↔sim redirection).
- Response fidelity is bounded by input-schema-only OpenAPI synthesis; the synthesizer is
  pluggable for a future "enhanced" generator.
- Harness session limits (≈100 messages, ~1h idle, queue depth 8) apply; the plugin
  auto-resets on session expiry, so simulated throughput is lower than the real backend.

# Skillberry "Simulate This" Plugin

Stand up a **simulated parallel vMCP** for a skill — a second vMCP whose tools are
backed by a containerized simulation-harness instead of the real backends — and flip a
plugin-owned switch deciding whether consumers reach the real or the simulated vMCP.

## How it works

- **Simulate this** builds a simulation skill + simulated tool manifests (MCP-packaged,
  pointing at the harness), creates a parallel vMCP referencing them, launches the harness
  container, and records the real/sim pair in a registry (`active="real"`).
- **Toggle real/sim** flips the active vMCP for a skill. It takes effect on the consumer's
  **next** resolve+connect — there is no mid-session redirection (between-runs contract).
- **Resolve**: consumers call `GET /plugins/simulate/active/{skill_uuid}` at the start of
  each use and connect to the returned `mcp_url`. The response includes `mode` (`real`/`sim`).
- **Tear down** deletes the sim vMCP, its tools and skill, stops the harness, and reverts.

## Configuration

See `.env.example`. Requires `SIMULATE_LLM_API_KEY` and a reachable Docker runtime.

## Limitations (v1)

- Whole-surface switch (the whole skill flips together), not per-tool.
- Between-runs switching only (no mid-session real↔sim redirection).
- Response fidelity is bounded by input-schema-only OpenAPI synthesis; the synthesizer is
  pluggable for a future "enhanced" generator.
- Harness session limits (≈100 messages, ~1h idle, queue depth 8) apply; the plugin
  auto-resets on session expiry, so simulated throughput is lower than the real backend.

# skillberry-plugin-dast

**DAST** (Dynamic Application Security Testing) — dynamically tests a **skill** by
discovering its externally-invocable entry points, exercising each with
adversarial inputs, and **observing the effects** (MCP calls, network egress,
subprocess spawns, filesystem access). Results are recorded under
`extra["dast"]` + `dast:` tags.

This is the **dynamic** counterpart to the store's static analyzers (SAST,
provenance, dependency-tracker): instead of reading code, it *runs* it with
hostile inputs and watches what it actually does.

## Threat model

A skill is reusable **code**, not just its agent-mediated behavior — any external
component (an agent, a developer, another tool) can load it and call its functions
directly. So DAST targets **all enumerable entry points**, not just agent usage.

## Entry points exercised (Phase 1)

| Tier | What | Source |
|------|------|--------|
| **Tier 1** | registered tools (name + parameter schema) | tool metadata |
| **Tier 2** | public top-level functions / classes / `__main__` | AST of the skill's modules |

Tier 2 functions that shadow a registered tool are de-duped into Tier 1.

## How it works

1. **Discover** entry points (Tier 1 from tool metadata, Tier 2 via AST).
2. **Generate inputs** for each via the optional Hypothesis engine — strategies
   mapped from each parameter's declared type, plus missing-required cases
   (deterministic; requires the engine, see below).
3. **Exercise** each case via the store's `FileExecutor` (Docker exec sandbox),
   with a pass-through-and-log **observe-shim** prepended to the code that
   records `socket`/`requests`/`httpx`/`urllib`/`subprocess`/`os.system`/`open`.
4. **Observe MCP** via a **benign vMCP twin** (`VirtualMcpServer`) the skill calls
   instead of the real server — faithful execution + per-call logging.
5. **Report** findings + coverage to `extra["dast"]`.

## Honest ceilings (in every report's `coverage`)

- **Discovery is static** → dynamically-dispatched entry points (Tier 3) may be
  missed → `coverage.exercised = N/M`.
- **Observation is detect-and-report, not prevent** → egress/effects *happen* and
  are recorded, not blocked → `coverage.observation = "detected, not prevented"`.
  **Run only against an operator-accepted network/sandbox.** True network lockdown
  is a follow-up gated on a runspace capability request.

## Live vs. dry-run

Real Docker + vMCP execution is gated behind **`DAST_LIVE=1`** (keeps the default
and CI inert). Without it, `scan` performs discovery + fuzzing through the full
pipeline with an inert executor — useful for inspecting entry points/coverage
offline. Set `DAST_LIVE=1` (with Docker available) to actually exercise code.

## The `extra["dast"]` block

```jsonc
{
  "schema_version": 1, "generated_at": "<ISO-8601>",
  "scanner": { "plugin_version", "mode": "detect-and-report", "live": false },
  "coverage": { "entry_points_discovered": M, "exercised": N, "skipped": ..,
                "by_tier": {"tool":..,"function":..,"class":..,"main":..},
                "discovery": "static (Tier-3 dynamic dispatch may be missed)",
                "observation": "detected, not prevented" },
  "entry_points": [ {"name","kind","module","params_or_signature","exercised"} ],
  "findings": [ {"entry_point","kind":"crash|leak|network-egress|subprocess|filesystem|mcp-call",
                 "severity":"high|medium|low|info","case","evidence","target"} ],
  "skipped_entry_points": [ {"name","reason"} ],
  "summary": { "findings","high","medium","egress_attempts","subprocess_attempts",
               "crashes","mcp_calls" }
}
```

Tags: `dast:findings:K`, `dast:coverage:N/M`, `dast:high:H`, `dast:egress:E`.

## API

Mounted at `/plugins/dast` (and `/api/plugins/dast/...`):

- `POST /scan` — `{ "object_type": "skill|tool|snippet", "uuid": str }` → `{ success, message, data }`. Invalid input → clean **400**.

**On-demand only** — no auto-scan-on-import hook.

## Input generator — an OPTIONAL open-source engine

Like the SAST plugin (which treats **bandit** as an optional engine), the DAST
scanner does **not** bundle an input generator. The supported engine is
**[Hypothesis](https://hypothesis.readthedocs.io)** (property-based testing).

- If Hypothesis is **not installed**, the scanner reports **disabled**
  (`is_enabled() == False`) and `POST /scan` returns **503** — there is no
  proprietary fallback generator.
- Install it to enable scanning:
  `pip install 'skillberry-plugin-dast[hypothesis]'`

All adversarial inputs are drawn from Hypothesis strategies mapped from each
parameter's declared type (string/int/float/bool/array/object, with a
type-confusion mix for unknown), plus missing-required cases. Draws are
deterministic for CI via a fixed seed.

- **Phase 2** (deferred): agent-mediated adversarial-prompt red-teaming, intended
  to wrap **garak** (NVIDIA). **mcp-scan/snyk-agent-scan** is a complementary
  static MCP taxonomy reference.

## Install / Test

```bash
pip install -e 'plugins/skillberry-plugin-dast[hypothesis]'   # engine enables scanning
pytest plugins/skillberry-plugin-dast/tests -q   # offline; real runs need DAST_LIVE=1 + Docker
```

Tests that generate inputs are skipped when the Hypothesis engine is absent; the
disabled-state path is always tested.

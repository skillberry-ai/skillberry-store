# Skillberry Plugin: Skill Optimizer

Optimizes existing Skillberry skills using a RunSpace-powered Claude Code session.

## What it does

1. Exports the selected skill to a temporary directory in Anthropic format
2. Stages optional context (skill metadata, execution trajectories, additional context)
3. Runs a RunSpace optimization session (Claude Code in container or local mode)
4. Imports the optimized result as a new skill in the store
5. Attaches full optimization metadata (rationale, changes, issues addressed) to the new skill

## Configuration

Copy `.env.example` to `.env` and fill in credentials:

```bash
ANTHROPIC_API_KEY=your_key_here
# or
ANTHROPIC_BASE_URL=https://your-proxy.example.com
ANTHROPIC_AUTH_TOKEN=your_token
```

Or configure `~/.claude/settings.json` (auto-detected).

## Execution modes

- `container` (default): Claude Code runs in a Docker container. Requires Docker.
- `local`: Claude Code runs on the host machine. Faster, for development only.

Set via `RUNSPACE_MODE` environment variable.

## API

`POST /api/plugins/skill-optimizer/optimize-skill`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `skill_uuid` | string | yes | UUID of the skill to optimize |
| `output_skill_name` | string | no | Override the auto-generated name |
| `include_metadata` | bool | no (default: true) | Include skill tags/extra in context |
| `trajectories_dir` | string | no | Path to execution trajectories folder |
| `additional_context_dir` | string | no | Path to additional context folder |
| `execution_mode` | string | no | `"container"` or `"local"` |
| `max_turns` | int | no | Max conversation turns (default: 300) |

## Output skill naming

- Default: `<original_name>_optimized`
- If taken: `<original_name>_optimized(1)`, `(2)`, ...
- Override with `output_skill_name`

## Optimization metadata

After optimization, the new skill's extra metadata contains an `optimization` key with:
- `optimization_rationale`: what was changed and why
- `issues_addressed`: failure modes fixed
- `tools_added / tools_modified / tools_removed`: tool changes
- `snippets_added / snippets_modified / snippets_removed`: snippet changes
- `source_skill_uuid`: UUID of the original skill
- `source_skill_name`: name of the original skill

# skillberry-plugin-doc-generator

**Documentation Generator & Enricher** — generates documentation where it is
missing, enriches thin docs without discarding author content, and detects drift
when an object's code or interface changes. Works for **skills, tools, and
snippets**, producing one consistent documentation shape across the catalog.
Addresses [#201](https://github.com/skillberry-ai/skillberry-store/issues/201).

The store has plugins to *assess* objects (security, SAST, provenance, dedupe,
evaluation) and to *improve code* (optimizer), but nothing maintains their
**documentation** — the description, usage, parameters, and examples that decide
whether anyone can understand and reuse an object. This plugin fills that gap.

## Documentation shape

Every object type gets the same shape (stored under `extra["documentation"]`):

| Field         | Meaning                                                   |
|---------------|-----------------------------------------------------------|
| `description` | Clear summary of what the object is/does                  |
| `when_to_use` | Usage / when-to-use guidance                              |
| `parameters`  | Per-input docs (`name`, `type`, `required`, `description`)|
| `examples`    | At least one usage example                                |
| `mode`        | `generated` / `enriched` / `kept` (vs. author content)    |
| `notes`       | Honesty notes about what could not be inferred            |

## Operations

- **Generate** — produce docs for an object that lacks them, derived from its own
  code, content, parameter schema, tags, and (for skills) referenced children.
- **Enrich** — expand thin author docs **without discarding** what the author
  wrote (`mode: enriched`); good author content is kept verbatim (`mode: kept`).
- **Refresh / drift** — `refresh` compares the object's current
  `source_fingerprint` (code/params/references) against the applied docs and
  flags drift, then proposes regenerated docs.

Generation is **review-before-apply** by default: results are stored under
`extra["documentation"].proposed` until applied (`apply=true`), which promotes
them to `extra["documentation"].current`. On import, the plugin auto-*proposes*
docs for objects that lack them (it never auto-applies).

## Generation backend

Documentation is produced by a frontier model through **`llm-switchboard`**,
wired exactly like the **security evaluator** plugin:

```
get_llm(LLM_PROVIDER) → Client(model_name=LLM_MODEL) → await client.generate_async(prompt=...)
```

Configure the provider in the environment (no UI), the same vars the other
LLM plugins use:

- `LLM_PROVIDER` (default `openai.async`), `LLM_MODEL` (default `gpt-4`)
- the provider's API key (e.g. `OPENAI_API_KEY`)

No specific model is hardcoded — the host chooses which one to plug in. If
`llm-switchboard` is not installed or the LLM cannot be initialized, the plugin
is **disabled** (`is_enabled()` is `False`) and its endpoints return `503`,
exactly like the security plugin. The `mode` label (`generated` / `enriched` /
`kept`) is decided from the author's existing description so the non-destructive
guarantee holds: sufficient author content is kept verbatim.

## API

Mounted at `/plugins/doc_generator` by the store (and `/api/plugins/doc_generator/...` for the UI):

- `POST /generate` — body `{ "object_type": "skill|tool|snippet", "uuid": str, "apply"?: bool, "only_if_missing"?: bool }`
- `POST /refresh`  — body `{ "object_type": "skill|tool|snippet", "uuid": str }`

Both return `{ success, message, data }`.

## UI

No custom UI: the plugin declares its actions via `get_ui_config()`, rendered by
the store's generic plugin action form (mirrors the SAST/provenance plugins).

## Install

```bash
pip install -e plugins/skillberry-plugin-doc-generator
```

## Test

```bash
pytest plugins/skillberry-plugin-doc-generator/tests -q
```

Tests are network-free: the `llm-switchboard` client is mocked (an `AsyncMock`
returns canned JSON, like the security plugin's tests) and the plugin is
exercised against a mocked store.

## Notes

- **Non-destructive**: the raw object `description` field is never overwritten;
  applied docs live in the structured `extra["documentation"]` block.
- **Non-blocking**: auto-proposal on import is best-effort and never fails an
  import.
- This plugin is **informational/assistive** — it proposes documentation for a
  human to review.

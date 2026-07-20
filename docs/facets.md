# Facets

The facets mechanism provides the small, cheap "what values exist?" answer
that filter-picker widgets in the UI need — the set of tags, namespaces,
and lifecycle states currently present across a collection — decoupled
from listing the collection itself.

## Why facets exist

Before server-side pagination the UI could compute pickers itself. Every
page mount loaded the full slim list of skills / tools / snippets /
vMCPs / vNFSs and derived the tag / namespace / state picker options
client-side with a `Set` walk.

Server-side pagination broke that pattern: the UI now only sees one page
at a time. A tag picker built from the current page would list only the
values that happen to appear on that page — the user could not select a
tag whose only items live on page 7. Refetching the full list just to
enumerate values would defeat pagination.

Facets solve this with a dedicated small endpoint that returns only the
distinct values, not the items:

* One small round trip. Payload size is proportional to the number of
  distinct tags / namespaces / states, not to the number of items. At
  5,000 snippets the paged list is ~20 KB per page; facets is typically
  a few KB total and cached for 60s in the UI.
* Every value in the store — not just the ones on the current page.
* Independent lifecycle from the paginated list — the pickers do not
  churn when the user pages, sorts, or filters.

## Wire shape

```
GET /facets/{snippets|skills|tools|vmcp_servers|vnfs_servers}
```

Response:

```json
{
  "tags":       ["python", "search", "utility"],
  "namespaces": ["prod", "staging"],
  "states":     ["approved", "draft"]
}
```

Each list is deduplicated and sorted. The `namespace:` prefix used
internally on tags is stripped in the `namespaces` list — `namespace:prod`
in an item's `tags` surfaces as `"prod"` under `namespaces`, not `tags`.

## Server implementation

Layered like the existing list / search endpoints:

* [services/facets.py](../src/skillberry_store/services/facets.py) — pure
  helper `compute_facets(items)` that walks a sequence of item dicts
  once, splits `namespace:*` tags into the namespaces bucket, collects
  `state`, and returns sorted lists. No I/O.
* Each service (skills, tools, snippets, vMCP, vNFS) exposes a
  `.facets()` method that hands the full list of cached dicts to the
  helper. Nothing is enriched — `running` / `runtime` / `_populate`
  never run for a facets call, so the endpoint does no server-manager
  fan-out and no cross-service lookups.
* The FastAPI handler is one line: translate exceptions to HTTP,
  return `service.facets()`.

Because `compute_facets` walks the raw cache dicts and does not touch
the runtime, the cost is one `handler.list_all_dicts()` plus a linear
scan. There is no separate index; the cost is bounded by the number of
items, and the payload it produces is bounded by the number of distinct
values.

## UI usage

Each page that has a tag / namespace picker mounts one `useQuery` for
facets, keyed by object type, alongside its paged list query:

```ts
const facetsQuery = useQuery({
  queryKey: ['skills', 'facets'],
  queryFn: skillsApi.facets,
  staleTime: 60_000,
});

const allTags       = facetsQuery.data?.tags       ?? [];
const allNamespaces = facetsQuery.data?.namespaces ?? [];
```

The 60-second `staleTime` matters: paging, searching, sorting, and
filtering the main table do NOT refetch facets. TanStack Query serves
the cached value until the store mutates (create / update / delete
invalidates `['skills']` and friends) or the stale window elapses.

## Interaction with `?fields` and pagination

Facets, `?fields`, and pagination are three orthogonal concerns:

* **`?fields`** trims the projection of each returned item — narrower
  wire payload per item.
* **`?limit` / `?offset`** trim which items are returned — page instead
  of full list.
* **`/facets/{type}`** trims what "list" means entirely — return only
  the distinct filter-picker values, no items.

The UI combines them: the main table uses `listPaged` with `fields=list`
and a page window; the pickers use `/facets/{type}`; semantic search
uses `searchProjected` on `/search/{type}`. Every widget requests only
what it needs.

## When facets do not apply

* **Small / bounded collections that already fit in one page.** The UI
  can safely enumerate values from the loaded list; adding a facets
  round trip is pure overhead.
* **A picker over a field with no dedicated facet.** Only `tags`,
  `namespaces`, and `states` are exposed today. A picker over, say,
  `author` would need either a new facet bucket or a different design.
* **A picker that must reflect the current filter set** (e.g. "tags
  present among items also tagged `prod`"). Facets are computed over
  the full collection, not over a filtered subset. Post-filter facets
  would need query params on `/facets/{type}`, which is not implemented.

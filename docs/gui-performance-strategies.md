# Strategies for Scaling the Skillberry-Store GUI to Large Object Counts

Author: analysis snapshot, 2026-07-01
Scope: `src/skillberry_store/ui` (React + PatternFly + TanStack Query + Vite) and
its collaborating FastAPI list endpoints under `src/skillberry_store/fast_api`.

---

## 1. What is actually slow — root causes

The symptoms (long page load, "kill this tab?" from the browser, worst on the
Snippets page) are the product of **four independent bottlenecks that compound**:

### 1.1 Server returns the full object on every list call

- [`GET /snippets/`](../src/skillberry_store/fast_api/snippets_api.py#L82) →
  [`SnippetsService.list_all`](../src/skillberry_store/services/snippets_service.py#L200) →
  `handler.list_all_dicts()` returns **every field of every snippet, including
  `content`** — which is the entire snippet body (may be kilobytes to hundreds of
  kilobytes per row). With 5K+ snippets this can easily exceed 50–200 MB of
  JSON on the wire.
- [`GET /skills/`](../src/skillberry_store/fast_api/skills_api.py#L85) →
  [`SkillsService.list_all`](../src/skillberry_store/services/skills_service.py#L290)
  runs [`populate_objects`](../src/skillberry_store/services/skills_service.py#L146)
  **for every skill**, which resolves every `tool_uuid` and `snippet_uuid`
  reference into a **full inlined object** (including snippet `content` again).
  For 972 skills that reference ~2K tools and thousands of snippets, this
  materializes a huge cross-product payload — the same snippet body may appear
  inlined in many skills.
- [`GET /tools/`](../src/skillberry_store/fast_api/tools_api.py) also returns the
  full tool manifest (params/returns/dependencies) for every row.

### 1.2 Client fetches ALL rows on every page mount

Every list page uses `useQuery({queryKey: ['<type>'], queryFn: <api>.list })`
with no `limit`/`offset` and a 30-second `staleTime`
(`ui/src/main.tsx:18`). The Skills page additionally pulls **all tools and all
snippets in parallel** so the "Create Skill" modal has data ready
([SkillsPage.tsx:103-112](../src/skillberry_store/ui/src/pages/SkillsPage.tsx#L103-L112)) —
even when the user only wants to browse skills.

### 1.3 Every row is rendered synchronously (no virtualization)

The PatternFly `Table` in [`SnippetsPage.tsx`](../src/skillberry_store/ui/src/pages/SnippetsPage.tsx#L457-L542)
and [`SkillListView.tsx`](../src/skillberry_store/ui/src/components/SkillListView.tsx#L27-L110)
maps directly over the filtered array. React reconciles ~5K rows × 6–7 cells
each = ~30K–40K DOM nodes on Snippets alone. Filtering, sorting, and typing
into the search box each rerun `useMemo` over the full array and rebuild the
whole table.

### 1.4 Background poll fully invalidates the massive queries

[`useChangesMonitor`](../src/skillberry_store/ui/src/hooks/useChangesMonitor.ts)
polls `/api/changes` every 5 s and, on any change bump, invalidates
`skills`/`tools`/`snippets` queries — triggering the whole 1.1 + 1.2 loop again.
During an import (which is when the store is most likely to have many items),
this fires continuously.

**Cost model of the current design** (order-of-magnitude, for 972 skills / 5K
snippets / 300 tools):

| Cost                       | Snippets page | Skills page                                     |
| -------------------------- | ------------- | ----------------------------------------------- |
| Backend serialization work | 5K JSON dumps | 972 × avg(fanout ≈ 8) ≈ 7–8K nested dumps       |
| Wire payload               | 50–200 MB     | 20–100 MB (often larger due to inlined content) |
| Browser parse + memo       | 5K objects    | 972 objects + inlined tools+snippets            |
| DOM nodes rendered         | ~35K          | ~7K (list view) / ~5K (card view)               |

Any single one of these is enough to cause the browser to warn.

---

## 2. Strategies

Six strategies below, from smallest change to largest. They are **not mutually
exclusive** — several combine well (Section 4).

### Strategy A — Server-side "list field selection" (slim payload)

**Idea:** the list endpoints keep their signatures but drop fields that the
list view never displays. New optional query param `?fields=list` (or a
dedicated `/snippets/summary`, `/skills/summary`, `/tools/summary`) returns
only what the table columns actually use.

For snippets, the list view uses only:
`uuid, name, description, state, content_type, version, tags, modified_at`
— **not** `content` or `extra`.

For skills, the list view uses:
`uuid, name, description, state, tags, version, tools.length, snippets.length,
modified_at`. We don't need to inline tool/snippet **objects**; a count
(`tool_count`, `snippet_count`) is enough for cards and rows. Detail page
still calls `GET /skills/{id}` and gets the fully populated view.

For tools, the list view uses:
`uuid, name, description, state, tags, module_name, version, modified_at` —
**not** `params`, `returns`, `dependencies`.

**Server work:**

- Add a field-selection helper in `object_handler.list_all_dicts` (or in the
  three services) that pops heavy fields when `fields=list`.
- In `SkillsService.list_all`, skip `populate_objects()` and instead compute
  counts from `tool_uuids`/`snippet_uuids` lengths.

**Client work:**

- Change `snippetsApi.list`, `skillsApi.list`, `toolsApi.list` to hit the slim
  variant. Add a `SnippetSummary`/`SkillSummary` TS type. Detail-page fetches
  are unchanged.

**Expected impact:** wire payload for Snippets falls from ~100 MB to ~2 MB
(a 50–100× reduction — most of the bytes are `content`). Skills payload
similarly. JSON parse and React memo pass drop proportionally. The 5K-row
render itself is still slow (see B).

| Aspect                | Value                                                                                                          |
| --------------------- | -------------------------------------------------------------------------------------------------------------- |
| Files changed         | ~5 backend (services + one shared helper), 3 client (`api.ts`, `types/index.ts`, references in the list pages) |
| Breaking API changes  | None if additive (`?fields=list`); mildly breaking if you change the default shape                             |
| Backend CPU / memory  | ↓↓ (no populate_objects, no `content` serialization)                                                           |
| Wire / browser memory | ↓↓↓                                                                                                            |
| DOM render cost       | Unchanged                                                                                                      |
| Risk                  | Low — additive, per-endpoint                                                                                   |
| Effort                | 0.5–1 day                                                                                                      |

---

### Strategy B — Client-side row virtualization

**Idea:** render only the ~30 rows currently in the viewport. Add
`@tanstack/react-virtual` (a peer of the already-used TanStack Query) or
`react-window`. This is a pure client change.

**Where to apply:**

- `SnippetsPage.tsx` — wrap the `<Tbody>` render in a virtualizer.
- `SkillListView.tsx` — same.
- `SkillCardView.tsx` — grid virtualization is slightly trickier but supported
  by both libraries; card row height is uniform.
- `ToolsPage.tsx` — same as snippets.

PatternFly's `Table` supports virtualization via its `VirtualizedTable`
component or via a custom `Tbody`. `@tanstack/react-virtual` is the smaller,
more flexible choice.

**Expected impact:** DOM node count for a page becomes O(viewport), independent
of dataset size. Sort/filter still re-runs across the whole in-memory array —
but the array is small compared to the DOM, so this cost is minor if we also
`useMemo`+`useDeferredValue` the search term. Does **not** help network cost or
memory footprint of the underlying data.

| Aspect                | Value                                                                     |
| --------------------- | ------------------------------------------------------------------------- |
| Files changed         | 4 UI files, plus 1 dep addition                                           |
| Breaking API changes  | None                                                                      |
| Backend CPU / memory  | Unchanged                                                                 |
| Wire / browser memory | Unchanged                                                                 |
| DOM render cost       | ↓↓↓                                                                       |
| Risk                  | Low; testable in isolation                                                |
| Effort                | 0.5 day for list views; 1 day if you also want card-grid virtualization   |
| Caveat                | Standalone this alone will _not_ fix Snippets — the payload is still huge |

---

### Strategy C — Server-side pagination + server-side search/sort/filter

**Idea:** the list endpoints stop returning the whole world. Instead,
`GET /snippets/?limit=50&offset=0&search=foo&tags=python&sort=modified_at:desc`
returns `{ items: [...], total: 4972, next_offset: 50 }`. The client keeps a
page in state and fetches page-at-a-time.

**Server work:**

- Extend list endpoints with `limit`, `offset` (or `cursor`), `sort`, and a
  simple substring `search` (over name/description), plus `tags`/`namespace`
  filters. The `DictCache` layer already has everything in memory, so filtering
  is O(N) but N is bounded — fast for 5K items.
- Move the sort/filter code currently in `filteredSnippets` `useMemo` blocks
  server-side. Semantic-search already exists on the server; that path stays as
  is.

**Client work:**

- Replace `useQuery` with `useInfiniteQuery` (from TanStack Query) or a
  paginated `useQuery` keyed by `(search, tags, page)`.
- Debounce the search input (200–300 ms) before firing the query. Filters/sort
  update the query key rather than a `useMemo`.
- Combine with virtualization (B) if you want a single scrolling list; combine
  with a classic pager if you want fixed page-size UX.

**Expected impact:** first paint returns 50 items = O(KB) instead of MB.
Backend CPU is bounded per page. Combined with B, memory is bounded too.

| Aspect                | Value                                                                                                                                            |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Files changed         | 3–4 backend (3 endpoints + service filter helper), 4–6 client (`api.ts`, `types`, 3 list pages, possibly a shared `useListQuery` hook)           |
| Breaking API changes  | The list endpoints change shape (`items+total` rather than a bare array). The CLI and any external consumer are affected — mitigate via `?legacy=1` or a version flag |
| Backend CPU / memory  | ↓↓ per request (bounded page size)                                                                                                               |
| Wire / browser memory | ↓↓↓                                                                                                                                              |
| DOM render cost       | ↓↓ (small page); ↓↓↓ combined with virtualization                                                                                                |
| Risk                  | Medium — touches API contract, CLI, and every list page                                                                                          |
| Effort                | 1.5–3 days                                                                                                                                       |
| Nice property         | Client-side tag/namespace enumeration (`allTags` `useMemo`) also has to move server-side or become a `/facets` endpoint — a nice cleanup         |

---

### Strategy D — Streaming list (NDJSON or SSE) with progressive render

**Idea:** the server keeps a "return everything" contract but streams objects
one line at a time (NDJSON) or as SSE events. The client processes each chunk
as it arrives and appends to the table.

**Server work:**

- Add a streaming endpoint: `GET /snippets/stream` returning
  `application/x-ndjson`. Use a FastAPI `StreamingResponse` that pulls from
  `handler.iter_dicts()` (already exists — see `object_handler.py:1028`) and
  writes `json.dumps(item) + "\n"` per row. No buffering.
- Or reuse SSE — same idea, more overhead per event.

**Client work:**

- Use `fetch` + `ReadableStream` + a line-splitting reader. Push rows into
  React state in batches (e.g., every 100 rows or every 50 ms via
  `requestAnimationFrame`) to avoid render thrash.
- Cancel the stream on unmount.

**Expected impact:** first row visible almost immediately; the browser is
never blocked on a giant JSON parse. The **total** amount of data transferred
is still huge unless you also apply field selection (A) — so this is a UX-only win
if used alone.

| Aspect                | Value                                                                                                                     |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Files changed         | 3 backend endpoints + 1 helper; 1 client streaming helper + 3 list pages                                                  |
| Breaking API changes  | Additive (new endpoint)                                                                                                   |
| Backend CPU / memory  | ↓ (server no longer buffers a giant string); still serializes all rows                                                    |
| Wire / browser memory | Unchanged unless combined with A                                                                                          |
| DOM render cost       | Unchanged unless combined with B                                                                                          |
| Risk                  | Medium — streaming edge cases (backpressure, timeouts, mid-stream error); TanStack Query doesn't cache streams as neatly  |
| Effort                | 1–2 days plus test hardening                                                                                              |
| Best for              | Very large, always-growing datasets when you _want_ the client to hold all items (e.g. for global client-side search)     |

---

### Strategy E — Search-first UX ("no upfront list")

**Idea:** the default view is empty (or a small "recent" slice, ~20 items)
plus a prominent search box. Users only load results when they type or apply a
filter. This flips the assumption that the user needs to see all items at once
— for 5000 snippets, no human scrolls through them.

**Server work:**

- Add a lightweight `GET /snippets/recent?limit=20` (or reuse `limit`/`offset`
  from Strategy C).
- Search endpoint is already there (`/search/snippets`) and is what powers
  "semantic" mode today — extend it to accept a plain-text mode server-side.

**Client work:**

- Reshape the list page: on mount, show "Type to search — 4972 snippets in
  store" with the recent 20. Full list is opt-in behind a "Show all" button
  that in turn kicks a paginated fetch.
- Reuse the existing `SearchBox` component; make "text" mode issue a
  server-side query instead of filtering an in-memory array.

**Expected impact:** first paint is instant. This is arguably the best UX for
5K+ items because scrolling through them is not a real workflow anyway. Cost
lives with the search endpoint, which is already indexed.

| Aspect                | Value                                                                                                                             |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Files changed         | 3 list pages (heavier), 1 backend if extending search; combines naturally with A/C                                                |
| Breaking API changes  | None if additive                                                                                                                  |
| Backend CPU / memory  | ↓↓↓                                                                                                                               |
| Wire / browser memory | ↓↓↓                                                                                                                               |
| DOM render cost       | ↓↓↓                                                                                                                               |
| Risk                  | Product/UX risk: "I want to see everything" workflows (export-all, bulk-tag) need explicit affordances                            |
| Effort                | 1–1.5 days                                                                                                                        |
| Caveat                | Bulk operations (export/delete "all matching") need a new "operate on entire result set, not just visible page" API, e.g. `/snippets/bulk-delete?filter=...`  |

---

### Strategy F — Client-side micro-optimizations

**Idea:** keep the API as is, but reduce the CPU cost of the current React
tree. This is the smallest possible change and buys the least.

Concrete moves:

- Wrap `filteredSnippets` search term with `useDeferredValue` so typing stays
  responsive.
- Memoize row components (`React.memo(SnippetRow)`).
- Precompute `allTags` / `allNamespaces` once, indexed on the server via a
  `/facets` endpoint (nice to have anyway).
- Bump `staleTime` for the big lists to `5 * 60 * 1000` and tighten the
  `useChangesMonitor` invalidation to only invalidate the type that actually
  changed (already possible if `/api/changes` returns per-type counts — check
  before assuming).
- Turn off `useChangesMonitor` polling while a page is fetching (avoid
  invalidation thrash during imports).

**Expected impact:** typing feels faster, background refetches are less
disruptive, but a 5000-row initial render still stalls the main thread.

| Aspect                | Value                                                        |
| --------------------- | ------------------------------------------------------------ |
| Files changed         | 3–5 UI files                                                 |
| Breaking API changes  | None                                                         |
| Backend CPU / memory  | Unchanged                                                    |
| Wire / browser memory | Unchanged                                                    |
| DOM render cost       | ↓ (marginal)                                                 |
| Risk                  | Very low                                                     |
| Effort                | 0.5 day                                                      |
| Note                  | Best treated as _polish_ once one of A/B/C/E is in place     |

---

## 3. Side-by-side comparison

Legend: ↓ small win, ↓↓ big win, ↓↓↓ dominant win, — no change.

| Strategy                    | Wire payload | Backend CPU | Browser CPU / mem | DOM render | Breaking API? | Effort  | Composes with     |
| --------------------------- | ------------ | ----------- | ----------------- | ---------- | ------------- | ------- | ----------------- |
| A. Slim list field selection| ↓↓↓          | ↓↓          | ↓↓                | —          | Additive      | 0.5–1 d | B, C, D, E, F     |
| B. Row virtualization       | —            | —           | ↓↓                | ↓↓↓        | No            | 0.5–1 d | A, C, D, E, F     |
| C. Server pagination+search | ↓↓↓          | ↓↓          | ↓↓↓               | ↓↓         | Yes (major)   | 1.5–3 d | A, B, E, F        |
| D. NDJSON/SSE streaming     | —            | ↓           | Time-to-first-row ↓↓↓ | —      | Additive      | 1–2 d   | A, B              |
| E. Search-first UX          | ↓↓↓          | ↓↓↓         | ↓↓↓               | ↓↓↓        | Additive      | 1–1.5 d | A, C, F           |
| F. Client micro-fixes       | —            | —           | ↓                 | ↓          | No            | 0.5 d   | Any               |

### Notes on breakage

- The service, CLI, and MCP layer all consume the same FastAPI endpoints. The
  CLI's `list-*` commands assume a bare array (see `openapi_extra={"x-cli-name":
  "list-*"}` decorators). Any strategy that changes the response envelope
  (C) needs to be gated behind either a new endpoint (`/snippets/page`) or a
  `?legacy=1` fallback, or the CLI has to be updated in lockstep.
- Strategies A, D, E can all be strictly additive (new fields / new endpoints)
  with zero blast radius outside the browser.

---

## 4. Recommended combination

For 5K+ objects, no single strategy is optimal on its own:

- **A alone** cuts payload by ~50× but still renders 5K DOM rows.
- **B alone** does not fix the Snippets 100 MB fetch — the browser stalls
  before the first row.
- **C alone** works, but requires an API contract change and a rewrite of the
  in-page filtering/sorting/tag-enumeration logic.
- **E alone** is the cheapest end-state UX win, but breaks the "show me
  everything, let me multi-select and bulk-delete" flow unless bulk operations
  get their own filter-based API.

The **highest-value, lowest-risk staged plan** is:

1. **A (slim field selection)** — 1 day. Ship first. This alone will make the
   Snippets page usable at 5K items (small payload, fast parse). Pure additive,
   no client contract change beyond types.
2. **B (row virtualization)** — 1 day. Ship after A. Fixes the residual
   render cost so scrolling is smooth even at 10K rows.
3. **F (micro-fixes)** — half a day in parallel with B.
4. **E (search-first UX)** — optional next step. Reframes the Snippets page
   from "browse table" to "find and act". A separate discussion — it changes
   product feel, not just performance.
5. **C (server pagination)** — hold off until the store crosses ~50K items or
   until we want to eliminate client-side sort/filter entirely. A + B is
   sufficient at 5K–20K scale.

**Not recommended right now:** D (streaming). It is the cleverest option but
adds moving parts (backpressure, mid-stream error handling, cache invalidation
semantics) for a benefit that A+B already delivers.

---

## 5. Concrete first PR (if you agree)

- Add `?fields=list` (or a `/summary` sibling) to
  [`GET /snippets/`](../src/skillberry_store/fast_api/snippets_api.py#L82),
  [`GET /skills/`](../src/skillberry_store/fast_api/skills_api.py#L85),
  [`GET /tools/`](../src/skillberry_store/fast_api/tools_api.py). Server
  field selection = pop `content`, `params`, `returns`, `dependencies`, `extra`, and
  skip `populate_objects` in `SkillsService.list_all` (send `tool_count` /
  `snippet_count` instead).
- Add a `SnippetSummary` / `SkillSummary` / `ToolSummary` type alias in
  [`ui/src/types/index.ts`](../src/skillberry_store/ui/src/types/index.ts).
- Point `snippetsApi.list`, `skillsApi.list`, `toolsApi.list` at the new mode
  in [`ui/src/services/api.ts`](../src/skillberry_store/ui/src/services/api.ts).
- Update `filteredSnippets` / `SkillCardView` / `SkillListView` to use the
  slim type; detail pages stay on the full object type.
- Add a `useChangesMonitor` guard so an in-flight query is not immediately
  invalidated by a change tick.

This is the smallest coherent change that will make the browser stop asking
whether to kill the tab.

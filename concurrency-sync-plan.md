# Concurrency Synchronization Plan

## Overview

Introduce a read/write lock mechanism to coordinate concurrent access to the five
object types: **skill**, **tool**, **snippet**, **vmcp**, and **vnfs**.

**Scope:** The service logic layer is where locks are *acquired*. The `ObjectHandler`
is where the lock *mechanism* lives (per-UUID lock registry + a handler-level coarse
lock). Services call `handler.read_lock(uuid)` / `handler.write_lock(uuid)` as
context managers. A second coarse handler-level write lock protects the
`_fix_parent_chain_after_delete` chain-repair walk that touches sibling objects.

**Not in scope:** The `VirtualMcpServerManager` and `VirtualNfsServerManager` already
use `threading.RLock` internally and are left unchanged.

---

## Lock Assignment by Operation

| Operation | Lock mode | Applies to |
|---|---|---|
| `get`, `get_module`, `list_all`, `search` | read | all five services |
| `update`, `delete` | write (per-UUID) | all five services |
| `create` | none on the new UUID (it is new); handler-level mutex briefly during lock-slot creation | all five services |
| `start` (vmcp/vnfs) | write (per-UUID) | vmcp, vnfs — wraps both handler read and server_manager.add_server together |
| `_fix_parent_chain_after_delete` chain walk | handler-level coarse write lock | ObjectHandler internal |
| `initialize_services` guard | module-level threading.Lock | registry.py |

---

## Sub-Tasks

---

### Sub-Task 1 — Add `fasteners` dependency

**Intent**
Add `fasteners` as a project dependency so `fasteners.ReaderWriterLock` is
available for import.

**Expected Outcomes**
- `fasteners` appears in the project's dependency declaration (`pyproject.toml`
  or `setup.cfg` / `requirements*.txt` — whichever is authoritative).
- `import fasteners` succeeds in the project's virtual environment.

**Todo List**
1. Locate the authoritative dependency file (e.g. `pyproject.toml`).
2. Add `fasteners` (no version pin required unless the project pins all deps) to
   the runtime dependencies list.
3. Verify `fasteners.ReaderWriterLock` is importable after the change.

**Relevant Context**
- Root-level `pyproject.toml` or `setup.cfg`
- The `fasteners.ReaderWriterLock` provides `.read_lock()` and `.write_lock()`
  context managers directly — no wrapper class is needed.

**Status:** [x] done

---

### Sub-Task 2 — Extend `ObjectHandler` with the lock registry

**Intent**
Give each `ObjectHandler` instance:
1. A **per-UUID `ReaderWriterLock` registry** with a short-lived mutex to protect
   registry insertions.
2. A **handler-level coarse `ReaderWriterLock`** used exclusively for
   `_fix_parent_chain_after_delete` to prevent races when the chain-repair walk
   reads and writes sibling objects.
3. Two public context-manager methods — `read_lock(uuid)` and `write_lock(uuid)` —
   consumed by the service layer.

**Expected Outcomes**
- `ObjectHandler.__init__` initialises:
  - `self._uuid_locks: Dict[str, ReaderWriterLock]` (empty dict)
  - `self._uuid_locks_mutex: threading.Lock`
  - `self._handler_lock: ReaderWriterLock` (coarse, for chain repair)
- `handler.read_lock(uuid)` returns a context manager that acquires the read side
  of that UUID's RWLock, creating the lock entry if absent.
- `handler.write_lock(uuid)` returns a context manager that acquires the write
  side of that UUID's RWLock, creating the lock entry if absent.
- `_fix_parent_chain_after_delete` acquires `self._handler_lock.write_lock()`
  before starting the chain walk, and releases it on exit.

**Todo List**
1. Add `import threading` and `import fasteners` imports to `object_handler.py`.
2. In `ObjectHandler.__init__` (around line 128), initialise the three new
   attributes.
3. Add a private helper `_get_uuid_lock(uuid: str) -> ReaderWriterLock` that
   looks up or creates a lock in `_uuid_locks`, protected by `_uuid_locks_mutex`.
4. Add public `read_lock(uuid: str)` and `write_lock(uuid: str)` methods that
   delegate to `_get_uuid_lock(uuid).read_lock()` and `.write_lock()`.
5. Wrap the body of `_fix_parent_chain_after_delete` with
   `with self._handler_lock.write_lock():`.

**Relevant Context**
- `src/skillberry_store/modules/object_handler.py`
- `ObjectHandler.__init__` — line 117
- `_fix_parent_chain_after_delete` — line 335
- `fasteners.ReaderWriterLock` API: `.read_lock()` and `.write_lock()` are
  context managers; they are re-entrant on the same thread for the same lock type.

**Status:** [x] done

---

### Sub-Task 3 — Add locking to `ToolsService`

**Intent**
Wrap every public `ToolsService` method body with the appropriate lock so that
concurrent reads on the same UUID proceed in parallel while writes are exclusive.

**Expected Outcomes**
- `get`, `get_module`, `list_all`, `search` acquire `handler.read_lock(uuid)` for
  the resolved UUID (or no per-UUID lock for `list_all` / `search` which iterate
  all objects — those are naturally snapshot-safe via the cache or disk reads).
- `update`, `delete` acquire `handler.write_lock(uuid)` for the resolved UUID.
- `create` acquires no per-UUID lock (the UUID is brand new); the handler's
  internal `_uuid_locks_mutex` briefly protects lock-slot creation on first use.
- `add_from_python` follows the same pattern as `create`.
- `execute` (async) is a read-side operation on the stored module — acquires
  `handler.read_lock(uuid)`.
- `find_dependencies` is a pure computation over already-loaded data — no lock
  needed.

**Todo List**
1. In `get()` (line 323): resolve UUID first, then wrap the `_safe_read` call
   with `with self.handler.read_lock(uuid):`.
2. In `get_module()` (line 345): same pattern — resolve UUID, then wrap the file
   read with `with self.handler.read_lock(uuid):`.
3. In `update()` (line 494): wrap the entire method body (from after UUID
   resolution) with `with self.handler.write_lock(uuid):`.
4. In `delete()` (line 545): wrap the entire method body (from after UUID
   resolution) with `with self.handler.write_lock(uuid):`.
5. In `execute()` (line 144): wrap the `handler.read_dict` / `handler.read_file`
   calls with `with self.handler.read_lock(uuid):`.
6. Leave `create()` and `add_from_python()` without a per-UUID lock.

**Relevant Context**
- `src/skillberry_store/services/tools_service.py`
- UUID resolution happens via `_resolve_uuid()` / `handler.resolve_to_uuid_or_error()`
  — this must occur *before* acquiring the lock (resolution itself only reads
  `name_cache`, which is read-only after startup for the purposes of this task).

**Status:** [x] done

---

### Sub-Task 4 — Add locking to `SnippetsService`

**Intent**
Same pattern as Sub-Task 3 applied to `SnippetsService`.

**Expected Outcomes**
- `get` → `read_lock(uuid)`
- `update`, `delete` → `write_lock(uuid)`
- `create` → no per-UUID lock
- `list_all`, `search` → no per-UUID lock (iterate/aggregate; cache snapshot safe)

**Todo List**
1. In `get()`: resolve UUID, wrap `_safe_read` with `read_lock`.
2. In `update()`: wrap body after UUID resolution with `write_lock`.
3. In `delete()`: wrap body after UUID resolution with `write_lock`.
4. Leave `create()`, `list_all()`, `search()` unchanged.

**Relevant Context**
- `src/skillberry_store/services/snippets_service.py`
- `SnippetsService` has no file-level operations (no `get_module` equivalent).

**Status:** [x] done

---

### Sub-Task 5 — Add locking to `SkillsService`

**Intent**
Same pattern applied to `SkillsService`. Note that `populate_objects` calls
`get_service("tool").get(...)` and `get_service("snippet").get(...)` internally —
those calls will acquire their own service locks, which is safe (no cross-service
deadlock possible since the lock graph is acyclic: skill → tool/snippet, never
the reverse).

**Expected Outcomes**
- `get` → `read_lock(uuid)` (includes the `populate_objects` call)
- `update`, `delete` → `write_lock(uuid)`
- `create`, `import_anthropic` → no per-UUID skill lock (new UUID); constituent
  tool/snippet creates are each lock-free on their own UUIDs too.
- `export_anthropic` → `read_lock(uuid)` (reads skill data)
- `detect_anthropic_skills` → no per-UUID lock (scans all, read-only)
- `list_all`, `search` → no per-UUID lock

**Todo List**
1. In `get()`: resolve UUID, wrap body with `read_lock`.
2. In `update()`: wrap body after UUID resolution with `write_lock`.
3. In `delete()`: wrap body after UUID resolution with `write_lock`.
4. In `export_anthropic()`: resolve UUID, wrap read body with `read_lock`.
5. Leave `create()`, `import_anthropic()`, `detect_anthropic_skills()`,
   `list_all()`, `search()`, `populate_objects()` without per-UUID locks.

**Relevant Context**
- `src/skillberry_store/services/skills_service.py`
- `populate_objects` is called inside `get()`, so it is already protected by
  the read lock acquired in step 1.

**Status:** [x] done

---

### Sub-Task 6 — Add locking to `VmcpService`

**Intent**
Same pattern, with the additional requirement that `start` and `delete` both
touch `server_manager` in addition to the handler. The write lock for `update`,
`start`, and `delete` must span *both* the handler operations and the
`server_manager` calls so a concurrent `start` and `delete` on the same UUID
cannot interleave.

**Expected Outcomes**
- `get` → `read_lock(uuid)` (wraps handler read + server_manager status check)
- `update` → `write_lock(uuid)` (wraps handler read/write + server_manager
  remove+add)
- `start` → `write_lock(uuid)` (wraps handler read + server_manager get+add)
- `delete` → `write_lock(uuid)` (wraps handler read + server_manager remove +
  handler delete)
- `create` → no per-UUID lock
- `list_all`, `search` → no per-UUID lock

**Todo List**
1. In `get()`: resolve UUID, wrap entire body with `read_lock`.
2. In `update()`: wrap body after UUID resolution with `write_lock`.
3. In `start()`: resolve UUID first, then wrap the check+start body with
   `write_lock(vmcp_uuid)`.
4. In `delete()`: wrap body after UUID resolution with `write_lock`.
5. Leave `create()`, `list_all()`, `search()` without per-UUID locks.

**Relevant Context**
- `src/skillberry_store/services/vmcp_service.py`
- `start()` has a TOCTOU race: `get_server` → not found → `add_server`. This is
  now closed by the write lock.
- `server_manager` has its own `RLock` — nesting is safe because `server_manager`
  calls are always leaf operations (they do not call back into the service).

**Status:** [x] done

---

### Sub-Task 7 — Add locking to `VnfsService`

**Intent**
Mirror of Sub-Task 6 for `VnfsService`.

**Expected Outcomes**
- `get` → `read_lock(uuid)`
- `update`, `start`, `delete` → `write_lock(uuid)`
- `create`, `list_all`, `search` → no per-UUID lock

**Todo List**
1. In `get()`: resolve UUID, wrap body with `read_lock`.
2. In `update()`: wrap body after UUID resolution with `write_lock`.
3. In `start()`: resolve UUID first, wrap check+start body with `write_lock`.
4. In `delete()`: wrap body after UUID resolution with `write_lock`.
5. Leave `create()`, `list_all()`, `search()` unchanged.

**Relevant Context**
- `src/skillberry_store/services/vnfs_service.py`
- Same `start` TOCTOU pattern as VMCP — closed by write lock.

**Status:** [x] done

---

### Sub-Task 8 — Guard `initialize_services` against concurrent init

**Intent**
Prevent a race condition where two threads simultaneously evaluate
`if not _initialized` as `True` and both proceed to construct and register services.

**Expected Outcomes**
- A `threading.Lock` (`_init_lock`) guards the `if _initialized` check-and-set in
  `initialize_services()`.
- `get_service()` and `clear_services()` are unchanged (they read/write
  `_initialized` under the GIL which is sufficient for their simpler access patterns,
  and `clear_services` is test-only).

**Todo List**
1. Add `import threading` to `registry.py`.
2. Add module-level `_init_lock = threading.Lock()`.
3. In `initialize_services()`, replace the bare `if _initialized:` guard with a
   `with _init_lock:` block that checks `_initialized`, performs all service
   construction, and sets `_initialized = True` inside the lock.

**Relevant Context**
- `src/skillberry_store/services/registry.py`
- `initialize_services` — line 24
- `_initialized` global flag — line 21

**Status:** [x] done

---

## Known Constraints and Notes

1. **`_resolve_uuid` is not locked** — name-to-UUID lookup reads `LookupCache`
   which is modified only inside write-locked operations. Reads without a lock are
   therefore safe (they see either the old or new HEAD, never a corrupted pointer).

2. **`list_all` / `search` iterate all objects** — These read every UUID's dict
   either from the in-memory `DictCache` (a Python dict; individual reads are
   GIL-safe) or from disk. They do not take a per-UUID lock. This matches the
   requirement that reads are permitted concurrently. A concurrent `delete` could
   cause a cache miss (404) for one item in the list; this is acceptable — the
   same item would already be absent in the next request.

3. **`get_cache_parent_for_head` in `create`** — This is called before `write_dict`
   and reads `name_cache`. It runs without a per-UUID lock (the UUID does not exist
   yet). Concurrent creates of objects with the *same name* could race on the parent
   chain. This is an existing data-integrity concern with the versioning model and is
   out of scope for this task.

4. **`fasteners.ReaderWriterLock` is writer-preferring by default** — This matches
   our intent: write operations get priority to avoid write starvation under heavy
   read load.

5. **Lock entry lifetime** — UUID lock entries in `_uuid_locks` are created on first
   use and never removed. For long-running processes with many objects this dict will
   grow; this is acceptable since each entry is a small object and the population is
   bounded by the number of ever-created objects.

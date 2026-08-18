# Build System Concepts

These concepts define how the Makefile system tracks repository state, decides when to
reinstall Python dependencies, and decides when to rebuild the Docker image. They form
a single "state → label → build" pipeline: repository state is fingerprinted into a
**git version label**, and downstream artifacts (installed dependencies, docker images,
version files) are invalidated only when that label — or a small set of well-defined
inputs — changes.

## 1. Git version label reflects repository state

A "git version" label is computed to identify the current state of the repository. The
label is a **pure function of state**, not of time or of environmental factors: the same
state always produces the same label, and any real change to state produces a different
label.

"State" is defined as **anything that `git status --porcelain` would report** at the
root of the working tree, together with the committed history reachable from `HEAD`.
Concretely, the label must change when any of the following occur:

- A new commit is made, amended, or checked out.
- A tracked file is modified, added, or removed in the working tree (whether staged or
  unstaged).
- A file is added to or removed from tracking (`git add`, `git rm --cached`).
- A new file appears in the working tree that is **not** matched by `.gitignore`.

The label must **not** change for events that do not affect state, including:

- Files that are matched by `.gitignore` (logs, build artifacts, virtual environments,
  the `.stamps/` directory itself, etc.) being created, modified, or removed.
- Remote refs being fetched, pruned, or otherwise updated without a corresponding local
  checkout.
- The passage of time between two invocations that observe the same state.

Because different sets of uncommitted changes must produce different labels, a bare
`-dirty` suffix is insufficient. When state is dirty, the label must incorporate a
fingerprint of the dirty content (for example, a short hash derived from
`git stash create`, or from the concatenation of `git diff HEAD` and the list of
non-ignored untracked files).

## 2. State manifest is content-idempotent and pivots the stamp graph

The primary artifact recording repository state is the **git-state manifest**
at `.stamps/git-version-manifest`. It is a canonical, byte-stable record of the
working-tree state whose content is a function of that state alone: same state
produces byte-identical manifest, and any real state change produces a
different manifest.

The manifest is content-idempotent: it is rewritten **only** when either:

1. It does not yet exist, or
2. Its new content differs from the content currently in the file.

The purpose is to keep the file's modification time stable across invocations
that do not change state. Anything downstream that depends on this file via
Make's timestamp rules must not re-fire spuriously. The manifest is the
**pivot of the stamp graph** — every downstream stamp that needs to know
"did state change" depends on it (see concept 4).

**Observability.** Because the manifest records per-file state, a rewrite is
also the natural place to report *what* changed. Whenever the manifest is
rewritten, an observability line is emitted:

- If no prior manifest exists: `No prior BUILD_VERSION detected`.
- Otherwise: `The following changes have been detected since previous BUILD_VERSION:` followed by the list of file paths responsible for the change, categorized (commit-delta `~`, newly-dirty `+`, no-longer-dirty `-`, still-dirty-with-different-content `!`).

**Optional projection to `VERSION_LOCATION`.** A project may additionally
declare `VERSION_LOCATION` — a path to an app-visible file (typically a
generated Python module) that carries the label at runtime. When defined,
this file is written with the *same* content-idempotence rule (rewritten only
when the label content differs), as a side effect of the manifest rewrite.
Projects that do not need runtime access to the label may leave
`VERSION_LOCATION` undefined; the manifest remains the pivot regardless.

This is a specific instance of a more general rule: **every generated file
that gates downstream builds must be content-idempotent** — rewritten only
when its content actually changes. The same discipline applies to any other
generated file that participates in the stamp graph.

## 3. Docker image presence is aligned with the git version label

The invariant enforced is: **a Docker image tagged with the current git version label
exists locally (or in the target registry, for registry builds)**. Build work is
performed only when necessary to restore that invariant.

A rebuild is performed when either:

1. No stamp records that an image for the current label has been produced, **or**
2. No local image with the current label tag actually exists (e.g., it was deleted
   with `docker rmi`).

An image obtained by pulling from a registry satisfies the invariant just as well as
one produced by a local build; the concept is **image presence at the current label**,
not "the build command was invoked." Stamp names should reflect the label so that
different labels never share a stamp:
`.stamps/docker-build-$(DBT)-$(BUILD_VERSION)` (or equivalent).

Local builds (`DBT=local`) and registry builds (`DBT=registry`) produce different
artifacts (a local image versus a pushed multi-arch manifest). They are tracked with
separate stamps and neither satisfies the other.

## 4. Change detection uses the state manifest, not a parallel scan

Any Make target that needs to know "did anything relevant change" must
consult the state manifest from concept 2 — directly, as a prerequisite. A
parallel scan-based mechanism (for example, `find`-with-mtime over a
hand-maintained list of subtrees) is **redundant** and must not be used,
because:

- It duplicates what git already tracks, and the two mechanisms will drift.
- Hand-maintained path lists rot as the codebase evolves.
- `mtime` is not preserved across `git checkout` and other git operations
  that rewrite files without changing their content, producing both false
  positives and false negatives.

Every stamp target that previously depended on such a parallel scan must be
migrated to depend on the state manifest.

## 5. `install-requirements-$(ODEPS)` has minimal, precise dependencies

The stamp for `install-requirements-$(ODEPS)` depends on exactly two things:

1. `pyproject.toml` — the source of dependency declarations.
2. The value of `ODEPS` — captured naturally by the per-value stamp name
   (`.stamps/install-requirements-$(ODEPS)`), so different `ODEPS` values get
   different stamps.

No other prerequisites are permitted on this stamp. In particular, the virtual
environment directory (`.venv`) must not be a prerequisite — its modification time is
not a reliable signal, and its existence is a precondition that belongs in a separate
`verify-venv` step that fails loudly if missing.

**Note on lockfiles**: this project currently installs directly from `pyproject.toml`
via `uv pip install -e .` without a lockfile. If a lockfile (`uv.lock`,
`poetry.lock`, `requirements*.txt`, etc.) is ever adopted, it becomes the ground
truth for what will actually be installed and must be added to the prerequisite list
alongside `pyproject.toml`.

## 6. Install stamp bookkeeping

When `install-requirements-$(ODEPS)` actually performs an installation, it must
enforce the following invariant on completion: **at most one non-empty-`ODEPS` stamp
is valid at any moment, and the empty-`ODEPS` stamp is always valid when any install
has occurred.**

The rationale is that `uv pip install -e .[X]` replaces the previous set of extras;
the environment reflects only the most recently installed extras, so any prior
non-empty stamp would be a lie about the environment. The empty-`ODEPS` case is
always implied because any `.[X]` install also installs the base package.

Concretely, on a successful install, the recipe must:

1. Remove **all** existing `.stamps/install-requirements-*` stamps.
2. Touch `.stamps/install-requirements-` (the empty-`ODEPS` stamp) — always.
3. If `ODEPS` is non-empty, additionally touch `.stamps/install-requirements-$(ODEPS)`.

On a **failed** install, no stamps are touched, so retry is forced on the next
invocation.

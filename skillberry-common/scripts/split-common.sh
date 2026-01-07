
#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  split-common.sh <SB_COMMON_REMOTE> <SB_COMMON_BRANCH> <SB_COMMON_PATH> [y]

Args:
  SB_COMMON_REMOTE  Name of git remote pointing at the subtree repository
  SB_COMMON_BRANCH  Branch name in the subtree repository (remote-tracking branch)
  SB_COMMON_PATH    Local path (relative to superproject root) where subtree is embedded
  y                 Optional. If provided as "y", and the new branch exists, replace it.

Behavior:
  - Ensures we are in a git repo and not in detached HEAD
  - Computes split SHA via: git subtree split -P <path> --rejoin
  - If split SHA is ancestor of <remote>/<branch>, roll back the --rejoin commit and abort
  - Otherwise create/update branch: <CURRENT_BRANCH>/<SB_COMMON_REMOTE>/<USERNAME> pointing to split SHA
  - Prints "Done" on success
EOF
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

note() {
  echo "INFO: $*" >&2
}

# Convert arbitrary string into a safe refname component
sanitize_ref_component() {
  local s="$1"
  # Trim
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"

  # Spaces -> underscores
  s="${s// /_}"

  # Remove/replace problematic ref chars: ~ ^ : ? * [ \ and control chars
  # Also avoid special rev syntax "@{", and slashes
  s="$(printf '%s' "$s" | tr -d '\000-\037' | sed -E \
    -e 's/[~^:?*\[\]\\]/_/g' \
    -e 's/\.\.+/_/g' \
    -e 's/@\{/_/g' \
    -e 's#/#_#g' \
    -e 's/_+/_/g' \
    -e 's/^_+//; s/_+$//')"

  [[ -n "$s" ]] || s="unknown"
  printf '%s' "$s"
}

# Extract a commit SHA from subtree output robustly (handles possible extra chatter)
extract_sha() {
  # Find the last 40-hex token in the output
  grep -Eo '([0-9a-f]{40})' | tail -n 1
}

# --- Parse args ---
if [[ $# -lt 3 || $# -gt 4 ]]; then
  usage
  exit 2
fi

SB_COMMON_REMOTE="$1"
SB_COMMON_BRANCH="$2"
SB_COMMON_PATH="$3"
REPLACE="${4:-}"

REPLACE_FLAG="n"
if [[ -n "$REPLACE" ]]; then
  [[ "${REPLACE,,}" == "y" ]] || die "Fourth argument, if provided, must be 'y'."
  REPLACE_FLAG="y"
fi

# --- Validate git repo and branch (not detached) ---
git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || die "Not inside a git work tree."

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" \
  || die "Unable to determine repository root."
cd "$REPO_ROOT"

CURRENT_BRANCH="$(git symbolic-ref -q --short HEAD 2>/dev/null || true)"
[[ -n "$CURRENT_BRANCH" ]] || die "Detached HEAD detected. Please checkout a branch and retry."

# Require clean tree (we may create and then rollback a --rejoin commit)
if ! git diff --quiet || ! git diff --cached --quiet; then
  die "Working tree is not clean. Please commit/stash changes before running."
fi

# --- Sanity checks ---
git remote get-url "$SB_COMMON_REMOTE" >/dev/null 2>&1 \
  || die "Remote '$SB_COMMON_REMOTE' does not exist in this repository."

[[ -e "$SB_COMMON_PATH" ]] || die "Path '$SB_COMMON_PATH' does not exist at repo root."

REMOTE_REF="$SB_COMMON_REMOTE/$SB_COMMON_BRANCH"
git show-ref --verify --quiet "refs/remotes/$REMOTE_REF" \
  || die "Remote-tracking branch '$REMOTE_REF' not found. Did you fetch '$SB_COMMON_REMOTE'?"

# --- Determine username for branch naming ---
GIT_USERNAME="$(git config --get user.name || true)"
if [[ -z "$GIT_USERNAME" ]]; then
  EMAIL="$(git config --get user.email || true)"
  if [[ -n "$EMAIL" && "$EMAIL" == *"@"* ]]; then
    GIT_USERNAME="${EMAIL%%@*}"
  fi
fi
GIT_USERNAME="$(sanitize_ref_component "${GIT_USERNAME:-unknown}")"

NEW_BRANCH="${CURRENT_BRANCH}/${SB_COMMON_REMOTE}/${GIT_USERNAME}"

git check-ref-format --branch "$NEW_BRANCH" >/dev/null 2>&1 \
  || die "Computed branch name is not a valid git ref: '$NEW_BRANCH'"

BRANCH_EXISTS="n"
if git show-ref --verify --quiet "refs/heads/$NEW_BRANCH"; then
  BRANCH_EXISTS="y"
fi

# If branch exists and replace not requested, abort early BEFORE creating a --rejoin commit
if [[ "$BRANCH_EXISTS" == "y" && "$REPLACE_FLAG" != "y" ]]; then
  die "Branch '$NEW_BRANCH' already exists. Re-run with 4th argument 'y' to replace it."
fi

note "Current branch:           $CURRENT_BRANCH"
note "Target split branch:      $NEW_BRANCH"
note "Remote comparison target: $REMOTE_REF"
note "Subtree path:             $SB_COMMON_PATH"
if [[ "$BRANCH_EXISTS" == "y" && "$REPLACE_FLAG" == "y" ]]; then
  note "Replace mode:             enabled (existing branch will be moved)"
fi

# --- Capture pre-split HEAD to rollback --rejoin if needed ---
PRE_SPLIT_HEAD="$(git rev-parse HEAD)"

# --- Compute split SHA (no branch created yet) ---
# This may create a rejoin commit on CURRENT_BRANCH.
SPLIT_OUT="$(git subtree split -P "$SB_COMMON_PATH" --rejoin 2>&1 | tee /dev/stderr)"
SPLIT_SHA="$(printf '%s\n' "$SPLIT_OUT" | extract_sha || true)"

[[ -n "$SPLIT_SHA" ]] || die "Failed to extract split SHA from git subtree output."

REMOTE_SHA="$(git rev-parse "$REMOTE_REF")"

note "Computed split SHA:       $SPLIT_SHA"
note "Remote branch HEAD:       $REMOTE_SHA"

# --- If no new commits for subtree PR: rollback --rejoin commit and abort ---
if git merge-base --is-ancestor "$SPLIT_SHA" "$REMOTE_REF"; then
  note "No new commits: split SHA is already contained in '$REMOTE_REF'."

  # Roll back the (new) --rejoin commit created by this run (if any).
  NOW_BRANCH="$(git symbolic-ref -q --short HEAD 2>/dev/null || true)"
  if [[ "$NOW_BRANCH" == "$CURRENT_BRANCH" ]]; then
    git reset --hard "$PRE_SPLIT_HEAD" >/dev/null
    note "Rolled back '$CURRENT_BRANCH' to remove the --rejoin commit from this run."
  else
    die "Unexpected branch state: currently on '$NOW_BRANCH'. Refusing to reset. Manually reset to $PRE_SPLIT_HEAD if needed."
  fi

  die "Nothing to submit for a PR."
fi

# --- Create or move the branch to the split SHA ---
# Only now do we create/update NEW_BRANCH.
if [[ "$BRANCH_EXISTS" == "y" && "$REPLACE_FLAG" == "y" ]]; then
  git branch -f "$NEW_BRANCH" "$SPLIT_SHA" >/dev/null
  note "Updated existing branch '$NEW_BRANCH' -> $SPLIT_SHA"
else
  git branch "$NEW_BRANCH" "$SPLIT_SHA" >/dev/null
  note "Created branch '$NEW_BRANCH' -> $SPLIT_SHA"
fi

echo "Done"

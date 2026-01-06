#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------------------------
# make-pr-common.sh
#
# Creates a PR in the "common" repo based on subtree changes in SB_COMMON_PATH.
#
# Inputs (arguments):
#   SB_COMMON_REMOTE   - git remote name for the common repo (must exist)
#   SB_COMMON_BRANCH   - base branch in common repo (e.g., main)
#   SB_COMMON_PATH     - subtree folder path (e.g., skillberry-common)
#
# Behavior:
#   - No fetch is performed. Uses local refs for SB_COMMON_REMOTE/SB_COMMON_BRANCH.
#   - Aborts early if no new subtree content compared to local remote-tracking ref.
#   - Pushes subtree content to a new branch on SB_COMMON_REMOTE (creates branch remotely).
#   - Uses gh pr create -e to open editor for title/body.
#   - Uses GH_REPO to target the common repo without needing --repo.
# ------------------------------------------------------------------------------

usage() {
  cat <<'EOF'
Usage:
  make-pr-common.sh <REMOTE> <BRANCH> <PATH>

Args:
  REMOTE  - git remote name used for the subtree (e.g., upstream-libfoo)
  BRANCH  - branch name on that remote (e.g., main)
  PATH  - path to the subtree directory in this repo (e.g., third_party/libfoo)

Creates a PR of the PATH-specific split of commits compared to the head of BRANCH in REMOTE.

Examples:
  make-pr-common.sh upstream-libfoo main third_party/libfoo
  make-pr-common.sh vendor-libbar master deps/libbar
EOF
}

# Accept -h/--help as well as missing args
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -ne 3 ]]; then
  usage >&2
  exit 2
fi

SB_COMMON_REMOTE="$1"
SB_COMMON_BRANCH="$2"
SB_COMMON_PATH="$3"

PR_COMMON_BRANCH_PREFIX="${PR_COMMON_BRANCH_PREFIX:-pr/common}"

die() { echo "ERROR: $*" >&2; exit 1; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

need_cmd git
need_cmd sed
need_cmd gh

# Ensure we run from repo root (safer)
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || die "Not inside a git repository"
cd "$REPO_ROOT"

BRANCH=""
BASE_REF=""
REMOTE_PUSHED=0
PR_CREATED=0

cleanup() {
  # Don't let cleanup errors mask the original failure
  set +e

  # If PR wasn't created but we pushed the remote branch, delete it
  if [[ "$PR_CREATED" -eq 0 && "$REMOTE_PUSHED" -eq 1 && -n "$BRANCH" ]]; then
    echo "==> PR was not created; deleting remote branch ${SB_COMMON_REMOTE}/${BRANCH}"
    # Delete remote branch (ignore failures)
    git push "$SB_COMMON_REMOTE" --delete "$BRANCH" >/dev/null 2>&1 || true
  fi

  # Always delete local PR branch if it exists
  if [[ -n "$BRANCH" ]] && git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
    echo "==> Deleting local branch ${BRANCH}"
    git branch -D "$BRANCH" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

# Ensure the remote exists (per requirement: assume it exists; fail if missing)
git remote get-url "$SB_COMMON_REMOTE" >/dev/null 2>&1 \
  || die "git remote '$SB_COMMON_REMOTE' does not exist"

# No-fetch constraint: require local remote-tracking ref to exist
BASE_REF="refs/remotes/${SB_COMMON_REMOTE}/${SB_COMMON_BRANCH}"
git show-ref --verify --quiet "$BASE_REF" \
  || die "Missing local ref $BASE_REF (no fetch requested). Run: git fetch ${SB_COMMON_REMOTE} ${SB_COMMON_BRANCH}"

REMOTE_SHA="$(git rev-parse "$BASE_REF")"

# Compute subtree split commit representing current SB_COMMON_PATH content
SPLIT_SHA="$(git subtree split --prefix "$SB_COMMON_PATH" HEAD)"

# No changes check:
# If SPLIT_SHA is already reachable from the remote-tracking branch, nothing new to PR.
if git merge-base --is-ancestor "$SPLIT_SHA" "$REMOTE_SHA"; then
  echo "No changes detected in '${SB_COMMON_PATH}' relative to ${SB_COMMON_REMOTE}/${SB_COMMON_BRANCH}. Aborting."
  exit 0
fi

# Create a unique branch name
TS="$(date +%Y%m%d-%H%M%S)"
USER_SLUG="$(git config user.name 2>/dev/null | tr ' ' '-' | tr -cd '[:alnum:]-' | tr '[:upper:]' '[:lower:]' || true)"
[[ -n "$USER_SLUG" ]] || USER_SLUG="user"
BRANCH="${PR_COMMON_BRANCH_PREFIX}/${USER_SLUG}/${TS}"

echo "==> Pushing subtree '${SB_COMMON_PATH}' to ${SB_COMMON_REMOTE}:${BRANCH}"
git subtree push --prefix "$SB_COMMON_PATH" "$SB_COMMON_REMOTE" "$BRANCH"
REMOTE_PUSHED=1

# Derive GH_REPO from SB_COMMON_REMOTE URL
# Supports:
# - SSH:   git@host:org/repo.git
# - HTTPS: https://host/org/repo.git
URL="$(git remote get-url "$SB_COMMON_REMOTE")"

HOST="$(echo "$URL" | sed -E 's#^git@([^:]+):.*#\1#; s#^https?://([^/]+)/.*#\1#')"
SLUG="$(echo "$URL" | sed -E 's#^git@[^:]+:##; s#^https?://[^/]+/##; s#\.git$##')"

[[ -n "$HOST" ]] || die "Failed to parse host from remote URL: $URL"
[[ -n "$SLUG" ]] || die "Failed to parse repo slug from remote URL: $URL"

REPO="${HOST}/${SLUG}"

echo "==> Creating PR in ${REPO}: ${BRANCH} -> ${SB_COMMON_BRANCH}"
# -e / --editor: opens editor for title/body (first line title, rest body)
# GH_REPO: tells gh which repo to operate on when not in that repo directory
GH_REPO="$REPO" gh pr create \
  --base "$SB_COMMON_BRANCH" \
  --head "$BRANCH" \
  -e
PR_CREATED=1

echo "==> Done."

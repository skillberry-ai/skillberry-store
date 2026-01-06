#!/usr/bin/env bash
set -euo pipefail

# Script for creating a PR: the PR target is provided as argument, and if not provided, it is auto-detected 
# from the git repository. If there are new commits compared to target branch head (recommended running "git fetch" before this script),
# then a PR can be created. In that case, a new unique branch is generated and pushed into, and then a PR is created using gh CLI.

die() { echo "ERROR: $*" >&2; exit 1; }
need_cmd() { command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"; }

need_cmd git
need_cmd gh
need_cmd tr
need_cmd date
need_cmd sed

# 1) Check we are in a git repository
git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || die "Not inside a git repository. Please run this from within a git working tree."

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[[ "$CURRENT_BRANCH" != "HEAD" ]] || die "Detached HEAD state. Please checkout a branch first."

# 0) Optional argument TARGET_BRANCH.
# If not provided, auto-detect from origin/HEAD (remote default branch).
TARGET_BRANCH="${1:-}"

if [[ -z "${TARGET_BRANCH}" ]]; then
  # Prefer symbolic-ref because origin/HEAD is typically a symref to origin/<default>
  if git symbolic-ref -q --short refs/remotes/origin/HEAD >/dev/null 2>&1; then
    # e.g. "origin/main" -> "main"
    TARGET_BRANCH="$(git symbolic-ref -q --short refs/remotes/origin/HEAD | sed 's#^origin/##')"
  else
    die "No TARGET_BRANCH provided and cannot auto-detect default branch: refs/remotes/origin/HEAD is not set.
Fix: run 'git remote set-head origin -a' (may contact the remote) and try again."
  fi
fi

# Resolve TARGET_BRANCH to a local or remote-tracking ref (prefer local)
BASE_REF=""
if git show-ref --verify --quiet "refs/heads/${TARGET_BRANCH}"; then
  BASE_REF="refs/heads/${TARGET_BRANCH}"
elif git show-ref --verify --quiet "refs/remotes/origin/${TARGET_BRANCH}"; then
  BASE_REF="refs/remotes/origin/${TARGET_BRANCH}"
else
  die "Target branch '${TARGET_BRANCH}' not found locally (refs/heads) or as origin/${TARGET_BRANCH} (refs/remotes)."
fi

# 2) Check that HEAD has new commits compared to TARGET_BRANCH head
AHEAD_COUNT="$(git rev-list --count "${BASE_REF}..HEAD")"
if [[ "${AHEAD_COUNT}" -eq 0 ]]; then
  die "No new commits to PR: HEAD is not ahead of '${TARGET_BRANCH}' (ref: ${BASE_REF})."
fi

# 3) Create PR branch name: pr/TARGET_BRANCH/user/timestamp
USER_SLUG="$(git config user.name 2>/dev/null | tr ' ' '-' | tr -cd '[:alnum:]-' | tr '[:upper:]' '[:lower:]' || true)"
[[ -n "$USER_SLUG" ]] || USER_SLUG="user"
TS="$(date +%Y%m%d-%H%M%S)"

# Sanitize TARGET_BRANCH for inclusion in branch name.
TARGET_SAFE="$(echo "$TARGET_BRANCH" | tr -cd '[:alnum:]._/-' | sed -E 's#^/+##; s#/+$##')"
[[ -n "$TARGET_SAFE" ]] || die "TARGET_BRANCH became empty after sanitization; original was '${TARGET_BRANCH}'."

PR_BRANCH="pr/${TARGET_SAFE}/${USER_SLUG}/${TS}"

# Avoid collisions locally
if git show-ref --verify --quiet "refs/heads/${PR_BRANCH}"; then
  die "Local branch '${PR_BRANCH}' already exists."
fi

echo "==> Current branch: ${CURRENT_BRANCH}"
echo "==> Target branch:  ${TARGET_BRANCH} (ref: ${BASE_REF})"
echo "==> Ahead commits:  ${AHEAD_COUNT}"
echo "==> PR branch:      ${PR_BRANCH}"

# Create local branch ref pointing at HEAD (no checkout needed)
git branch "${PR_BRANCH}" HEAD

# 4) Push commits to the PR branch (remote: origin)
echo "==> Pushing to origin: ${PR_BRANCH}"
git push -u origin "refs/heads/${PR_BRANCH}:refs/heads/${PR_BRANCH}"

# 5) Create PR to TARGET_BRANCH from PR_BRANCH using gh with editor mode
echo "==> Creating PR: ${PR_BRANCH} -> ${TARGET_BRANCH}"
gh pr create -e --base "${TARGET_BRANCH}" --head "${PR_BRANCH}"

echo "==> Done."

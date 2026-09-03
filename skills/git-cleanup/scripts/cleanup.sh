#!/usr/bin/env bash
# cleanup.sh — prune stale local branches for a single git repo
#
# Usage:
#   bash cleanup.sh <repo-path> [--dry-run]
#
# Prints branches that track a deleted remote (": gone]" in git branch -vv),
# deletes them with git branch -D, and reports what was removed.
# With --dry-run, only lists what would be deleted without touching anything.

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: cleanup.sh <repo-path> [--dry-run]" >&2
  exit 1
fi

REPO="$1"
DRY_RUN="${2:-}"

if [ ! -d "$REPO/.git" ]; then
  echo "[SKIP] Not a git repo: $REPO"
  exit 0
fi

cd "$REPO"

# Sync remote state
git fetch --prune --quiet 2>/dev/null || true

# Find branches whose remote tracking branch is gone.
# awk handles the leading '*' on the currently checked-out branch.
STALE=$(git branch -vv | grep ': gone]' | awk '{print ($1 == "*") ? $2 : $1}' || true)

if [ -z "$STALE" ]; then
  echo "[OK]   $REPO — no stale branches"
  exit 0
fi

echo "[FOUND] $REPO"
while IFS= read -r branch; do
  echo "        $branch"
done <<< "$STALE"

if [ "$DRY_RUN" = "--dry-run" ]; then
  echo "[DRY]  Would delete $(echo "$STALE" | wc -l | tr -d ' ') branch(es) — run without --dry-run to delete"
  exit 0
fi

DELETED=0
while IFS= read -r branch; do
  git branch -D "$branch" && DELETED=$((DELETED + 1)) || echo "[WARN] Could not delete $branch (may be checked out)"
done <<< "$STALE"

echo "[DONE] Deleted $DELETED branch(es) from $REPO"

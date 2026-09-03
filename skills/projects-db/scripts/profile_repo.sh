#!/usr/bin/env bash
# profile_repo.sh — detect a repo's roster fields for projects-db.md
#
# Usage:
#   bash profile_repo.sh <repo-path>
#
# Prints one tab-separated line: name<TAB>path<TAB>language<TAB>branch<TAB>context-docs
# Stores nothing; writing the row into projects-db.md is the skill's job.

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: profile_repo.sh <repo-path>" >&2
  exit 1
fi

REPO="$1"

if [ ! -d "$REPO" ]; then
  echo "ERROR: not a directory: $REPO" >&2
  exit 1
fi

# Resolve to an absolute path without requiring realpath everywhere.
REPO_ABS=$(cd "$REPO" && pwd)
NAME=$(basename "$REPO_ABS")

# --- language: manifest/lockfile first, then most common source extension ---
detect_language() {
  if [ -f "$REPO_ABS/package.json" ]; then
    # tsconfig or .ts files => TypeScript, else JavaScript
    if [ -f "$REPO_ABS/tsconfig.json" ] || ls "$REPO_ABS"/**/*.ts >/dev/null 2>&1; then
      echo "TypeScript"; return
    fi
    echo "JavaScript"; return
  fi
  [ -f "$REPO_ABS/pyproject.toml" ] || [ -f "$REPO_ABS/requirements.txt" ] || [ -f "$REPO_ABS/setup.py" ] && { echo "Python"; return; }
  [ -f "$REPO_ABS/go.mod" ] && { echo "Go"; return; }
  [ -f "$REPO_ABS/Cargo.toml" ] && { echo "Rust"; return; }
  [ -f "$REPO_ABS/pom.xml" ] || [ -f "$REPO_ABS/build.gradle" ] || [ -f "$REPO_ABS/build.gradle.kts" ] && { echo "Java"; return; }
  echo "unknown"
}
LANGUAGE=$(detect_language)

# --- default branch: origin/HEAD, else current branch, else "-" ---
detect_branch() {
  local b
  b=$(git -C "$REPO_ABS" symbolic-ref --quiet refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@') || true
  if [ -n "${b:-}" ]; then echo "$b"; return; fi
  b=$(git -C "$REPO_ABS" branch --show-current 2>/dev/null) || true
  echo "${b:--}"
}
BRANCH=$(detect_branch)

# --- context docs: which of the repo's own standard docs exist ---
CONTEXT_DOCS=""
for doc in README.md ARCHITECTURE.md CLAUDE.md CONTRIBUTING.md docs/architecture.md; do
  if [ -f "$REPO_ABS/$doc" ]; then
    CONTEXT_DOCS="${CONTEXT_DOCS:+$CONTEXT_DOCS, }$doc"
  fi
done
[ -z "$CONTEXT_DOCS" ] && CONTEXT_DOCS="(none)"

printf '%s\t%s\t%s\t%s\t%s\n' "$NAME" "$REPO_ABS" "$LANGUAGE" "$BRANCH" "$CONTEXT_DOCS"

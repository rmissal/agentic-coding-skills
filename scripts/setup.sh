#!/usr/bin/env bash
# setup.sh — bootstrap the agentic-coding-skills library on this machine.
#
# The committed source of truth is the neutral top-level skills/ directory.
# This script GENERATES the harness-specific discovery paths from it:
#   - repo-local:  .claude/skills/  and  .agents/skills/   (gitignored)
#   - user-scope:  ~/.claude/skills/ and ~/.agents/skills/ (every project sees them)
# Each is populated with per-skill links back to skills/<name> (edits sync live)
# plus the upstream skill-creator + mcp-builder skills installed under vendor/.
#
# Idempotent. Re-run any time. Pass --no-user-scope to skip the ~/ links.
#
# Windows: runs under Git Bash; directory junctions (mklink /J) need no admin.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_SRC="$REPO_ROOT/skills"
VENDOR="$REPO_ROOT/vendor/skills"
UPSTREAM_REPO="https://github.com/anthropics/skills.git"
UPSTREAM_SKILLS=(skill-creator mcp-builder)

USER_SCOPE=1
for arg in "$@"; do
  case "$arg" in
    --no-user-scope) USER_SCOPE=0 ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
  esac
done

_is_windows() { case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) return 0 ;; *) return 1 ;; esac; }

# _link_dir <link-path> <source-dir>: point link-path at source-dir. Never
# clobbers a real, populated directory (protects a user's own skills).
_link_dir() {
  local link="$1" src="$2"
  [ -d "$src" ] || { echo "  [skip] missing source: $src"; return; }
  mkdir -p "$(dirname "$link")"
  if _is_windows; then
    local wl ws; wl="$(cygpath -w "$link")"; ws="$(cygpath -w "$src")"
    cmd //c rmdir "$wl" >/dev/null 2>&1 || true   # removes a junction or empty dir; fails safely on a real one
    if [ -e "$link" ] && [ ! -L "$link" ]; then
      echo "  [keep] $link (existing non-empty dir, not replaced)"; return
    fi
    if cmd //c mklink //J "$wl" "$ws" >/dev/null 2>&1; then
      echo "  [link] $link"
    else
      echo "  [warn] could not create junction: $link"
    fi
  else
    if [ -e "$link" ] && [ ! -L "$link" ]; then
      echo "  [keep] $link (existing dir/file, not replaced)"; return
    fi
    rm -f "$link"
    ln -s "$src" "$link" && echo "  [link] $link"
  fi
}

# install_upstream: fetch skill-creator + mcp-builder into vendor/ (warn, don't fail, offline).
install_upstream() {
  echo "==> Installing upstream skills (skill-creator, mcp-builder)"
  local tmp; tmp="$(mktemp -d)"
  if ! git clone --depth 1 --filter=blob:none --sparse "$UPSTREAM_REPO" "$tmp" >/dev/null 2>&1; then
    echo "  [warn] could not clone $UPSTREAM_REPO (offline?). skill-creator/mcp-builder unavailable;"
    echo "         grade-skills will report the missing prerequisite until you re-run with a network."
    rm -rf "$tmp"; return
  fi
  git -C "$tmp" sparse-checkout set "skills/skill-creator" "skills/mcp-builder" >/dev/null 2>&1 || true
  mkdir -p "$VENDOR"
  local name src
  for name in "${UPSTREAM_SKILLS[@]}"; do
    src="$tmp/skills/$name"
    if [ -d "$src" ]; then
      rm -rf "${VENDOR:?}/$name"; mkdir -p "$VENDOR/$name"
      cp -r "$src/." "$VENDOR/$name/"
      echo "  [ok] vendored $name"
    else
      echo "  [warn] $name not found upstream (moved? check github.com/anthropics/skills)"
    fi
  done
  rm -rf "$tmp"
}

# assemble <dest-skills-dir>: link every committed skill + vendored upstream into dest.
assemble() {
  local dest="$1" d name
  echo "==> Assembling $dest"
  mkdir -p "$dest"
  for d in "$SKILLS_SRC"/*/; do
    name="$(basename "$d")"
    _link_dir "$dest/$name" "$SKILLS_SRC/$name"
  done
  for name in "${UPSTREAM_SKILLS[@]}"; do
    [ -d "$VENDOR/$name" ] && _link_dir "$dest/$name" "$VENDOR/$name"
  done
}

wire_hooks() {
  echo "==> Wiring git pre-commit hook"
  local cur; cur="$(git -C "$REPO_ROOT" config --get core.hooksPath || true)"
  if [ -z "$cur" ]; then
    git -C "$REPO_ROOT" config core.hooksPath scripts/git-hooks
    chmod +x "$REPO_ROOT/scripts/git-hooks/pre-commit" 2>/dev/null || true
    echo "  [ok] core.hooksPath -> scripts/git-hooks"
  elif [ "$cur" = "scripts/git-hooks" ]; then
    echo "  [ok] core.hooksPath already set"
  else
    echo "  [warn] core.hooksPath is '$cur' — leaving as-is (run: git config core.hooksPath scripts/git-hooks)"
  fi
}

seed_projects_db() {
  echo "==> Project roster"
  if [ -f "$REPO_ROOT/projects-db.md" ]; then
    echo "  [ok] projects-db.md already present"
  else
    cp "$REPO_ROOT/projects-db.md.example" "$REPO_ROOT/projects-db.md"
    echo "  [ok] created projects-db.md from example (gitignored)"
  fi
}

echo "agentic-coding-skills setup — source of truth: $SKILLS_SRC"
install_upstream
assemble "$REPO_ROOT/.claude/skills"
assemble "$REPO_ROOT/.agents/skills"
if [ "$USER_SCOPE" = 1 ]; then
  assemble "$HOME/.claude/skills"
  assemble "$HOME/.agents/skills"
else
  echo "==> Skipping user-scope links (--no-user-scope)"
fi
wire_hooks
seed_projects_db
echo "Done. The skills are discoverable by Claude Code and any agentskills.io-compatible agent."

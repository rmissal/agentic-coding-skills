#!/usr/bin/env python3
"""skill_audit.py — portability & functional-domain guardian for the skill library.

Fails (exit 1) when a committed file would make the library non-portable or a
skill drift out of its declared functional domain. This is the enforcement arm of
the `skill-quality` skill; it runs on demand and in CI.

Gates (see skills/skill-quality/SKILL.md for the rationale):
  1. Leaked machine-local content — absolute paths / emails (placeholders exempt).
  2. Brand / company terms — adopter-supplied portability-denylist.txt only; the
     committed repo ships no lexical brand list, staying brand-neutral itself.
  3. Hardcoded model IDs / tool names in SKILL.md prose (glob forms like
     `claude-*` / `mcp__*` are pattern references, not real IDs — exempt).
  4. Every SKILL.md declares a non-empty metadata.domain.
  5. No skill invents a per-repo *context*.md file (best-effort heuristic).
  6. Frontmatter validity — delegated to validate_skill_frontmatter.py.

Usage:
    py -3 skills/skill-quality/scripts/skill_audit.py
Exit codes: 0 = clean · 1 = one or more findings · 2 = harness error
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = REPO_ROOT / "skills"
FRONTMATTER_VALIDATOR = REPO_ROOT / "scripts" / "validate_skill_frontmatter.py"
DENYLIST_FILE = REPO_ROOT / "portability-denylist.txt"

try:
    import yaml  # type: ignore
except ImportError:
    sys.stderr.write("ERROR: PyYAML is required (pip install pyyaml).\n")
    sys.exit(2)

# --- placeholder exemptions --------------------------------------------------
# A "path-like" match is a real leak only if it is NOT one of these placeholder
# forms. Docs and templates legitimately show placeholder paths.
PLACEHOLDER_MARKERS = ("…", "...", "<", ">", "path/to", "path\\to", "path\\", "${", "your-", "/you/", "/username/")
PLACEHOLDER_USER_TOKENS = {
    "you", "your", "username", "your-username", "user", "name", "me", "path", "home",
}

# --- gate 1: absolute paths + emails -----------------------------------------
UNIX_ABS = re.compile(r"/(?:Users|home)/([A-Za-z0-9._-]+)")
# A real Windows path: drive letter at a boundary (not preceded by a word char or
# backslash, which would make it a regex escape like `\s` / `\n`), then `:\` and a
# word-char directory segment. This avoids matching regex source in scripts.
WIN_ABS = re.compile(r"(?<![\w\\])[A-Za-z]:\\[A-Za-z0-9_][^\s\"'`)\]|]*")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# --- gate 3: model IDs / tool names in prose ---------------------------------
# Requires a real versioned suffix (>=2 dash/dot segments), so glob forms like
# `claude-*` or `gpt-*` (pattern references) do not match.
MODEL_ID = re.compile(
    r"\b(?:claude|gpt|gemini|llama|mistral|qwen|opus|sonnet|haiku)-[a-z0-9]+(?:[-.][a-z0-9]+)+",
    re.IGNORECASE,
)
# A real MCP tool name has a lowercase letter after the prefix; `mcp__*` (glob) does not.
TOOL_NAME = re.compile(r"\bmcp__[a-z]")

# --- gate 5: per-repo context file -------------------------------------------
CONTEXT_FILE = re.compile(
    r"(?:creat|writ|generat|maintain)\w*\b[^.\n]{0,40}?\b[\w-]*context[\w-]*\.md",
    re.IGNORECASE,
)

TEXT_SUFFIXES = {
    ".md", ".py", ".sh", ".bat", ".ps1", ".json", ".yml", ".yaml", ".txt",
    ".toml", ".cfg", ".ini", ".js", ".ts",
}


def list_committed_files() -> list[Path]:
    """Tracked + untracked-not-ignored files (respects .gitignore)."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=False,
        )
        if out.returncode == 0 and out.stdout.strip():
            files = [(REPO_ROOT / line) for line in out.stdout.splitlines() if line.strip()]
            return [f for f in files if f.is_file()]
    except FileNotFoundError:
        pass
    # Fallback: walk, skipping known generated / vendored dirs.
    skip = {".git", ".agents", "node_modules", "__pycache__", "vendor"}
    result: list[Path] = []
    for p in REPO_ROOT.rglob("*"):
        if p.is_file() and not any(part in skip for part in p.relative_to(REPO_ROOT).parts):
            if not (p.parts[-3:-1] == (".claude", "skills")):
                result.append(p)
    return result


def is_placeholder(fragment: str) -> bool:
    low = fragment.lower()
    return any(m in low for m in PLACEHOLDER_MARKERS)


def read_text(path: Path) -> str | None:
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def load_denylist() -> list[re.Pattern[str]]:
    if not DENYLIST_FILE.exists():
        return []
    pats: list[re.Pattern[str]] = []
    for line in DENYLIST_FILE.read_text(encoding="utf-8").splitlines():
        term = line.strip()
        if term and not term.startswith("#"):
            pats.append(re.compile(re.escape(term), re.IGNORECASE))
    return pats


def scan_line_for_paths_and_emails(line: str) -> list[str]:
    findings: list[str] = []
    for m in UNIX_ABS.finditer(line):
        frag = m.group(0)
        user = m.group(1).lower()
        if is_placeholder(frag) or user in PLACEHOLDER_USER_TOKENS:
            continue
        findings.append(f"absolute path: {frag}")
    for m in WIN_ABS.finditer(line):
        frag = m.group(0)
        if is_placeholder(frag):
            continue
        findings.append(f"absolute path: {frag}")
    for m in EMAIL.finditer(line):
        frag = m.group(0)
        if "example." in frag.lower() or frag.lower().startswith(("you@", "user@", "name@")):
            continue
        findings.append(f"email: {frag}")
    return findings


def main() -> int:
    findings: list[str] = []
    files = list_committed_files()
    denylist = load_denylist()

    for path in files:
        # The denylist itself is the source of brand terms — never scan it.
        if path == DENYLIST_FILE:
            continue
        text = read_text(path)
        if text is None:
            continue
        relpath = rel(path)

        # Gates 1 + 2: run on every committed text file, line by line.
        for i, line in enumerate(text.splitlines(), 1):
            for hit in scan_line_for_paths_and_emails(line):
                findings.append(f"{relpath}:{i}  {hit}")
            for pat in denylist:
                if pat.search(line):
                    findings.append(f"{relpath}:{i}  brand/denylist term: {pat.pattern}")

    # Gates 3, 4, 5: SKILL.md prose only.
    skill_files = sorted(SKILLS_DIR.glob("**/SKILL.md"))
    for path in skill_files:
        text = read_text(path)
        if text is None:
            continue
        relpath = rel(path)

        for i, line in enumerate(text.splitlines(), 1):
            for m in MODEL_ID.finditer(line):
                findings.append(f"{relpath}:{i}  hardcoded model id in prose: {m.group(0)}")
            for m in TOOL_NAME.finditer(line):
                findings.append(f"{relpath}:{i}  hardcoded tool name in prose: {m.group(0)}")
            if CONTEXT_FILE.search(line):
                findings.append(f"{relpath}:{i}  skill appears to author a per-repo context file")

        # Gate 4: metadata.domain present + non-empty.
        fm = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.DOTALL)
        domain_ok = False
        if fm:
            try:
                data = yaml.safe_load(fm.group(1))
                domain = (data or {}).get("metadata", {}).get("domain")
                domain_ok = isinstance(domain, str) and domain.strip() != ""
            except yaml.YAMLError:
                domain_ok = False
        if not domain_ok:
            findings.append(f"{relpath}  missing or empty metadata.domain")

    # Gate 6: delegate frontmatter validity.
    fm_rc = 0
    if FRONTMATTER_VALIDATOR.exists():
        launcher = [sys.executable] if sys.executable else ["python3"]
        proc = subprocess.run(
            launcher + [str(FRONTMATTER_VALIDATOR)],
            cwd=REPO_ROOT, capture_output=True, text=True, check=False,
        )
        fm_rc = proc.returncode
        if fm_rc != 0:
            findings.append("frontmatter validator reported errors:\n" + proc.stderr.strip())

    if findings:
        sys.stderr.write("skill_audit: FAIL — portability / domain findings:\n\n")
        for f in findings:
            sys.stderr.write(f"  - {f}\n")
        sys.stderr.write(f"\n{len(findings)} finding(s). See skills/skill-quality/SKILL.md.\n")
        return 1

    print(f"skill_audit: OK — {len(files)} files, {len(skill_files)} skills clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

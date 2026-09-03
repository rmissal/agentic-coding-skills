#!/usr/bin/env python3
"""Validate every `skills/*/SKILL.md` frontmatter parses as strict YAML.

Guards against the "Nested mappings are not allowed in compact mappings"
class of errors — an unquoted YAML scalar that contains an embedded ": "
sequence trips strict parsers (js-yaml, pyyaml safe_load) even though
lenient parsers accept it.

This is a real-world failure mode: a single unquoted `description:` line with
an embedded colon-space silently breaks strict tooling that never ran locally.

Usage:
    py -3 scripts/validate_skill_frontmatter.py             # sweep repo
    py -3 scripts/validate_skill_frontmatter.py <path...>   # validate specific files

Exit codes:
    0 = all frontmatters parse
    1 = one or more failed (details printed to stderr)

Ships with zero business logic beyond parse-validity — the intent is a
fast, deterministic guard that plugs into pre-commit and CI. Richer schema
validation (name/description length, allowed keys) lives in the upstream
`skill-creator/scripts/quick_validate.py`, installed by setup.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable

try:
    import yaml  # type: ignore
except ImportError:
    sys.stderr.write(
        "ERROR: PyYAML is required (pip install pyyaml, or `py -m pip install pyyaml`).\n"
    )
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)


def discover_skill_files() -> list[Path]:
    """Every SKILL.md under skills/."""
    return sorted(SKILLS_DIR.glob("**/SKILL.md"))


def validate_one(path: Path) -> tuple[bool, str]:
    """Return (ok, reason)."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return False, f"cannot read: {e}"

    if not text.startswith("---"):
        return False, "no YAML frontmatter (file does not start with ---)"

    match = FRONTMATTER_RE.match(text)
    if not match:
        return False, "unterminated YAML frontmatter (missing closing ---)"

    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as e:
        # Compact one-line reason, keep the mark for line/col so authors know where
        first_line = str(e).splitlines()[0]
        return False, f"YAML parse error — {first_line}"

    if not isinstance(data, dict):
        return False, "frontmatter is not a mapping"

    return True, "ok"


def sweep(paths: Iterable[Path]) -> int:
    fails: list[tuple[Path, str]] = []
    ok_count = 0
    for path in paths:
        ok, reason = validate_one(path)
        if ok:
            ok_count += 1
        else:
            fails.append((path, reason))

    for path, reason in fails:
        try:
            rel = path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            # Path lives outside the repo (e.g. a test tmp file); use it as-is.
            rel = str(path)
        sys.stderr.write(f"FAIL  {rel}\n         {reason}\n")

    total = ok_count + len(fails)
    if fails:
        sys.stderr.write(
            f"\n{len(fails)} of {total} SKILL.md frontmatters failed strict YAML parse.\n"
            f"Fix: convert unquoted scalars containing colon-space (': ') to folded scalars:\n"
            f"    description: <one long line>\n"
            f"  becomes:\n"
            f"    description: >-\n"
            f"      <same long line>\n"
            f"See scripts/validate_skill_frontmatter.py for details.\n"
        )
        return 1
    print(f"OK — {total} SKILL.md files parse cleanly.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "paths",
        nargs="*",
        help="Specific SKILL.md files to validate. Omit to sweep the whole repo.",
    )
    args = parser.parse_args()

    if args.paths:
        # Filter to SKILL.md files that actually exist — silently skip anything
        # else, so the hook can be invoked with a broad staged-file list.
        paths = [Path(p) for p in args.paths if Path(p).name == "SKILL.md" and Path(p).exists()]
        if not paths:
            # Nothing to check → success; useful when the pre-commit hook fires
            # on a commit that touches no SKILL.md files.
            return 0
    else:
        paths = discover_skill_files()

    return sweep(paths)


if __name__ == "__main__":
    sys.exit(main())

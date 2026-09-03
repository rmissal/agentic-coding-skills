# CLAUDE.md

Portable conventions for the **agentic-coding-skills** library. These rules bind
any agent working *in this repo* (authoring or maintaining skills). They contain
no project-, company-, or domain-specific content by design — this repo is meant
to be published and reused anywhere.

## What this repo is

A standalone, brand-neutral library of Claude Code / agentskills.io **skills** that
encode general software-engineering practice: clean coding, requirements
engineering, PR finalization, test quality, output evaluation, git hygiene, plus
the meta-skills that create, grade, and guard the library itself. Nothing here is
tied to a specific language, framework, repository, model, or coding agent.

The skills live in the neutral top-level `skills/<name>/SKILL.md` — no coding
agent is privileged in the repo. `setup.sh` generates the harness-specific
discovery paths from that single source: per-skill links into `.claude/skills/`
(Claude Code) and `.agents/skills/` (agentskills.io / cross-tool), plus their
user-scope equivalents (`~/.claude/skills/`, `~/.agents/skills/`) so every
project and coding agent on the machine sees them. Those generated paths are
gitignored; `skills/` is the only committed copy.

## SKILL.md frontmatter — folded scalars for long fields (load-bearing)

The frontmatter is parsed by strict YAML tooling: `.github/workflows/ci.yml`, the
git pre-commit hook (`scripts/git-hooks/pre-commit`), and the upstream
skill-creator validator. Strict parsers reject unquoted scalars that contain a
colon-space sequence (`: `) — the pattern that produces
*"Nested mappings are not allowed in compact mappings"*.

Rule: **any long free-text field must use the folded scalar form (`>-`)**, not an
unquoted one-liner. Long text is anything with embedded quoted phrases (`"…"`),
URLs containing `://`, or *any* `: ` sequence. Applies to `description`,
`compatibility`, `whenToUse`.

```yaml
# ❌ Wrong — strict parsers reject on the ": " inside the quoted phrase
description: Use this skill to check "spec.md": expected outputs against actual.

# ✅ Right — folded scalar renders as a single-line paragraph for readers
description: >-
  Use this skill to check "spec.md": expected outputs against actual.
```

Short scalars stay unquoted — `name: my-skill`, `user-invocable: false`.

Run `py -3 scripts/validate_skill_frontmatter.py` after editing to sweep the whole
repo; pass a specific path to check one file. The pre-commit hook does this on
staged `SKILL.md` files; CI does it on every PR.

## Frontmatter keys

Every `SKILL.md` declares:

| key | required | purpose |
|---|---|---|
| `name` | yes | kebab-case skill id, matches its directory |
| `description` | yes | when to trigger; the routing signal (folded scalar) |
| `user-invocable` | no | `true` if reachable as `/<name>`; default `false` |
| `whenToUse` | no | extra trigger context (folded scalar if long) |
| `metadata.domain` | yes | one-line **functional domain** — what this skill is *for* |

The `metadata.domain` convention is what lets `skill-quality` detect scope-creep:
a skill's body must keep matching its declared domain. Self-improvement may sharpen
a skill, never widen its scope.

## Machine-local content rule

No usernames, absolute paths (`/Users/…`, `/home/…`, `C:\…`), emails, or
company/domain brand terms in committed files. Machine-local values belong in
`CLAUDE.local.md` (gitignored) or the machine-local `projects-db.md` roster — never
in the repo. Use `${HOME}`, `<your-username>`, or a generic `/path/to/…`
placeholder in docs and examples.

`scripts/skill_audit.py` (the `skill-quality` guardian) enforces this on every PR.

## Security posture

Never print secret or environment values. Never read `.env`, `*.secret`, or any
secrets directory (blocked in `.claude/settings.json`). Skills operate on code and
docs, not credentials.

## Teach-mode (opt-in)

By default, answer lean — the result, not a lecture. When the user's message
contains `explain`, `teach`, `why`, or a `--teach` marker, append a brief
**"Why this approach"** rationale (1–3 lines, citing the principle or source).
No rationale unless asked.

## Coding standards for this repo

Before pushing anything, follow the `finalize-and-open-pr` skill: run formatters,
the P1–P5 self-review, and open a PR via `gh`. Never push directly to `main`.
Adding a skill = one new `skills/<name>/SKILL.md` (+ optional `scripts/`,
`evals/`); no other files need editing. Keep each skill single-purpose and in its
declared `metadata.domain`.

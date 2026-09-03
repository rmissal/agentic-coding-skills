---
name: skill-quality
description: >-
  Use this skill to audit the skill library against the qualities that make it portable and trustworthy, so they can't be bypassed or watered down over time. Runs the automated guardian (scripts/skill_audit.py): no leaked absolute paths, emails, usernames, or brand/company terms; no hardcoded model IDs or agent/tool names baked into skill prose; every SKILL.md declares its metadata.domain; no skill invents a per-repo context file instead of reading the repo's own docs; frontmatter validity delegated to the frontmatter validator. Then applies a review rubric for the non-greppable qualities — single-purpose, in-domain, general-not-coupled. Trigger it after editing any skill, before a release, in CI, or when reviewing a self-improvement change that might have caused scope-creep. Orthogonal to grade-skills (trigger quality) and the frontmatter validator (YAML validity); this skill owns portability + functional-domain integrity.
user-invocable: true
metadata:
  domain: >-
    Guarding the library's portability and functional-domain integrity — no
    leaked context, no scope-creep, every skill in its declared domain.
---

# Skill Quality

The guardian that keeps the library what it claims to be: brand-neutral, portable,
and single-purpose — permanently, not just on the day it was extracted. Skills get
edited and self-improved over time; without a guard, coupling and scope-creep leak
back in. This skill is that guard.

It owns **one** of the three quality axes:
- **skill-quality** (this) — portability + functional-domain integrity.
- **grade-skills** — trigger/description correctness.
- **frontmatter validator** — YAML validity.

Each is orthogonal; this skill delegates frontmatter validity to the validator
rather than re-implementing it.

---

## Automated gates — `scripts/skill_audit.py`

Run on demand and in CI:

```bash
py -3 skills/skill-quality/scripts/skill_audit.py
```

It fails (exit 1) on any of:

1. **Leaked machine-local content** — absolute paths (`/Users/…`, `/home/…`,
   `C:\…`), email addresses, or OS usernames in any committed file. Placeholders
   (`/path/to/…`, `${HOME}`, `<your-username>`) are allowed.
2. **Brand / company terms** — matched against generic patterns plus an optional,
   adopter-supplied `portability-denylist.txt` at the repo root (one term per line).
   The committed repo ships **no** denylist of its own — staying brand-neutral even
   in its guard — so an adopter can add private terms without editing this skill.
3. **Hardcoded model IDs or tool/agent names in skill prose** — patterns like
   `claude-*`, `gpt-*`, `mcp__*`, or internal CLI names baked into a `SKILL.md`
   body. This scans **prose/bodies**, not `scripts/` — a script legitimately
   *defaulting* a model behind a `--model` flag is configurable and fine; a
   `SKILL.md` that hardcodes "run against `claude-<some-version>`" is not portable.
4. **Missing `metadata.domain`** — every `SKILL.md` must declare its one-line
   functional domain. Absent domain → fail.
5. **Per-repo context files** — a skill that writes a bespoke per-repo context file
   (instead of reading the repo's own README/ARCHITECTURE/CLAUDE/CONTRIBUTING) is
   flagged. Per-repo context belongs in the repo's own docs; the only machine-local
   roster allowed is `projects-db.md`.

Frontmatter validity is delegated: the audit invokes
`scripts/validate_skill_frontmatter.py` and folds its result in.

---

## Review rubric — the non-greppable qualities

Some qualities a regex can't check. When reviewing a skill (especially after a
self-improvement or optimization round), confirm by reading:

- **Single-purpose & in-domain.** Does the body still match the skill's declared
  `metadata.domain`? Self-improvement may *sharpen* a skill — clearer triggers,
  better examples, tighter prose — but must **never widen its scope**. A skill that
  has grown a second job needs splitting, not expanding.
- **General, not coupled.** Examples and prose stay generic. No reintroduced
  project-, tool-, or company-specific coupling that slipped past the regexes.
- **Multi-language / multi-project neutral.** The skill operates on whatever repo it
  runs in — no assumption of one language, one repo layout, or one toolchain.

If a change fails the rubric, the fix is to re-scope back to the declared domain, not
to update `metadata.domain` to match the creep. The domain is the contract; the body
serves it.

---

## When to run

- After editing or adding any skill.
- When reviewing a self-improvement / optimization change (the highest-risk moment
  for scope-creep).
- In CI on every PR (`scripts/skill_audit.py` runs alongside the frontmatter
  validator).
- Before a release, as a whole-library health check.

`skill-quality` is itself subject to its own gates — it is audited like every other
skill.

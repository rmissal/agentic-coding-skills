---
name: grade-skills
description: >-
  Use this skill to measure and improve how reliably skills trigger — whether each skill's description fires on the prompts it should and stays silent on the prompts it shouldn't. Runs a grading loop over the skill library: for each skill, it evaluates the trigger description against positive and negative example queries, scores selection accuracy, and can auto-optimize a weak description (rewriting it and re-grading until it improves). Use it after adding or editing a skill, when a skill misfires or fails to fire, or for a periodic library health check. Grades trigger correctness only — orthogonal to frontmatter YAML validity (the frontmatter validator) and to portability/domain integrity (skill-quality). Requires the upstream skill-creator skill and the `claude` CLI to be installed.
user-invocable: true
metadata:
  domain: >-
    Grading and auto-optimizing skill trigger descriptions for selection
    accuracy — does each skill fire on the right prompts and no others.
---

# Grade Skills

A skill only works if it triggers at the right moment. This skill measures that:
does each skill's `description` fire on prompts it should handle, and stay quiet on
prompts it shouldn't? Weak descriptions either never fire (dead skill) or fire
everywhere (noise). Grading catches both.

This is one of three orthogonal quality axes:
- **grade-skills** (this) — trigger correctness.
- **frontmatter validator** — YAML validity (folded-scalar rule).
- **skill-quality** — portability + functional-domain integrity.

---

## Prerequisites

The grader shells out to a real model to judge selection, so it needs:

- **The upstream `skill-creator` skill installed** — the grading loop reuses its
  eval runner. `setup.sh` installs it into the generated harness paths.
- **The `claude` CLI on PATH** — the model backend the grader queries.
- **Per-skill example queries** — each skill supplies `evals/queries.json` with
  positive examples (prompts that *should* select it) and negative examples
  (prompts that shouldn't). No queries → nothing to grade for that skill.

If any prerequisite is missing, the grader reports it and skips rather than
producing a misleading score.

---

## Running

```bash
# Grade the whole library
py -3 skills/grade-skills/scripts/grade_all.py --skills-root skills

# Grade one skill
py -3 skills/grade-skills/scripts/grade_all.py --skills-root skills --skill coding
```

Key flags:
- `--skills-root skills` — the committed source of truth (this repo's neutral skill dir).
- `--model <id>` — the judge model; defaults to a fast small model. Override to grade against whatever model your agent actually runs on.
- `--optimize` — after grading, rewrite descriptions that scored below their achievable best and re-grade. Only patches a skill's description in place when the rewrite genuinely scores higher than the original; otherwise it leaves the original untouched.

On Windows, [`scripts/windows_patch.py`](scripts/windows_patch.py) is applied
automatically to fix cross-platform issues (pipe handling, process pools, and
platform-independent skill discovery) before the eval loop runs.

---

## Reading the output

The grader reports, per skill, how many positive queries correctly selected it and
how many negative queries correctly did not. Interpret:

- **High positive + high negative** — healthy trigger. Leave it.
- **Low positive** — the description is too narrow or too vague; the skill won't fire when needed. Widen/clarify the *trigger conditions* (not the scope).
- **Low negative** — the description is too broad; the skill fires on unrelated prompts and crowds out others. Tighten it, add explicit "Do NOT use for…" boundaries.

Use `--optimize` to let the loop propose a better description, but review the diff —
an optimized description must still describe the *same* functional domain
(`metadata.domain`). Trigger optimization must never widen a skill's scope; that's a
`skill-quality` violation. Sharpen the wording, don't grow the job.

---

## When to run

- After adding a new skill (confirm it fires and doesn't shadow others).
- After editing a description or renaming a skill.
- When a skill misfires in practice — fails to trigger, or triggers on the wrong prompts.
- As a periodic library health check before a release.

Grading artifacts (`grades.json`, `grades_summary.json`) are regenerated on demand
and gitignored — they're a measurement, not a source of truth.

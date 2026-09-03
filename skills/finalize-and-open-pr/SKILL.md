---
name: finalize-and-open-pr
description: >-
  Use this skill right before pushing code or opening a pull request — whenever the user says "finalize", "open a PR", "ship it", "raise the PR", or you've finished a change and are about to push. Runs a disciplined pre-push sequence: discover and run the repo's own formatters and linters, execute the relevant tests, walk a P1–P5 self-review checklist (correctness, scope, tests, style, security), write a clear PR title/body/test-plan, create a feature branch (never push to the default branch), open the PR via the `gh` CLI, and triage any automated bot-review comments by severity. Prevents the two most common failures: pushing unformatted/untested code, and rubber-stamping your own diff. Do NOT use for merging PRs or for mid-development commits — only at the finalize-and-open step.
user-invocable: true
metadata:
  domain: >-
    The pre-push finalization gate: self-review, formatting, tests, and PR
    creation on a feature branch — never a direct push to the default branch.
---

# Finalize and Open PR

The gate between "I think it's done" and a PR others will trust. Reviewing is the
expensive step now — so review your *own* diff with the rigor you'd give someone
else's before asking anyone to look at it.

Never push to the default branch. Every change lands on a feature branch and goes
through a PR, no matter how small.

---

## Sequence

### Step 1 — Discover the repo's tooling
Don't assume a toolchain. Find what this repo actually enforces (see the `coding`
skill's Repo Discovery):
- Formatter/linter config: `pyproject.toml`, `ruff.toml`, `.eslintrc*`, `.prettierrc*`, `go.mod`, `Cargo.toml`, `Makefile`.
- CI workflows (`.github/workflows/*.yml`) — the authoritative list of what must pass.
- A wrapper target if one exists (`make lint`, `make ci`, `npm run ci`) — prefer it over reconstructing individual commands.

### Step 2 — Run formatters and linters
Run exactly what the repo pins, with its flags and versions. A wrong line length or
formatter version reformats files in a way CI will reject. If the repo pins nothing,
apply the language defaults from the `coding` skill.

### Step 3 — Run the tests
Run the test scope appropriate to the change (see the `test-quality` skill's
SMOKE/STANDARD/FULL ladder). Report real results — if tests fail, say so with the
output; never claim green you didn't see.

### Step 4 — P1–P5 self-review

Walk every item. This is the checklist that catches what fluency hides.

- **P1 — Correctness.** Does the change do what the requirement asked? Trace the actual behavior, not the commit message. Check edge cases and error paths. For AI-generated diffs specifically: grep every new API/flag/import to confirm it exists (no hallucinated calls).
- **P2 — Scope.** Does every hunk map to the stated task? Remove opportunistic refactors, renamed symbols, and unrelated touched files — silent scope creep is a review-killer. One PR, one concern.
- **P3 — Tests.** Every behavior change ships with a test change. Do the tests actually exercise the new path (not assert-nothing green)? Does fixture/mock data still match the real data shape?
- **P4 — Style & clarity.** Matches surrounding code's naming, comment density, and idioms? Formatter/linter clean? No dead code, no debug prints, no commented-out blocks.
- **P5 — Security & side effects.** No secrets, tokens, or machine-local paths in the diff. No destructive operation without a guard. Side-effecting steps warn-and-continue rather than abort after the effect is already live (see `coding`: Don't Abort on Already-Effective Side Effects).

If any item fails, fix it before proceeding. Don't open the PR on a known-failing item and hope the reviewer misses it.

### Step 5 — Branch
Create a feature branch off the default branch. Never commit the change directly on
the default branch even if the remote allows it.

```bash
git switch -c <type>/<short-slug>   # e.g. fix/cache-ttl, feat/report-export
```

### Step 6 — Commit + changelog
Write a clear commit message (imperative mood, explains *why*). If the repo keeps a
`CHANGELOG.md` or versions its releases, add the appropriate entry / version bump
following that repo's convention — check `CONTRIBUTING.md` or existing history for
whether it does. If the repo doesn't version, skip this.

### Step 7 — Push the branch
```bash
git push -u origin <branch>
```

### Step 8 — Open the PR
Prefer the `gh` CLI. Search for a PR template first (`.github/pull_request_template.md`
or `.github/PULL_REQUEST_TEMPLATE/`) and follow it if present.

```bash
gh pr create --title "<concise title>" --body "<summary + test plan>"
```

The body must include:
- **Summary** — what changed and why, in a few sentences.
- **Test plan** — the exact commands you ran and their results, so a reviewer can reproduce.

### Step 9 — Triage automated review comments
After opening, an automated reviewer (any `[bot]` account — Copilot, a linter bot, a
house review bot) may post comments. Triage by severity; don't reflexively "fix"
every suggestion.

| Severity | What it looks like | Action |
|---|---|---|
| **P1 — real defect** | correctness bug, security issue, broken edge case the bot correctly spotted | **Act on it** — fix, push, and reply noting the fix. |
| **P2 — style/opinion** | naming, formatting nit, subjective refactor suggestion | Apply if it's consistent with the repo's conventions; otherwise leave it. No reply needed. |
| **P3 — false positive** | the bot misread the code, flagged intended behavior, or hallucinated an issue | Leave it. No reply needed — don't argue with a bot in the thread. |

Only P1 warrants a code change + reply. P2/P3 don't need a response — resolve or
dismiss silently. Judge the comment on merit; a bot suggestion is not automatically
correct.

---

## Guardrails

- **Never push to the default branch.** No exceptions inside this skill — even a one-line follow-up chore goes through a branch + PR.
- **Never fabricate results.** If a formatter, test, or push step failed, report it and stop — don't open a PR claiming a clean run you didn't get.
- **Don't skip the self-review because the change is small.** Small diffs hide the most rubber-stamped bugs.
- **The PR is a live external effect.** Once `gh pr create` succeeds, a later failure (label, auto-merge, reviewer assignment) should warn and continue — the PR exists; don't roll back or pretend it doesn't.

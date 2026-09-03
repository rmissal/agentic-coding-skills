---
name: git-cleanup
description: >-
  Use this skill to prune stale local git branches — the ones whose upstream was deleted after a PR merged and now linger as "[gone]" in `git branch -vv`. Runs across one repo or every repo in your machine-local projects-db roster, safely deletes only branches git itself reports as gone (never unmerged or current branches), and supports a dry-run to preview first. Resolves repo paths from projects-db.md, falling back to a REPO_PATHS environment variable or an explicit path argument. Use it when the user says "clean up branches", "prune merged branches", "my branch list is a mess", or after a batch of PRs has merged. Do NOT use for deleting remote branches or for any history-rewriting operation.
user-invocable: true
metadata:
  domain: >-
    Pruning stale local git branches (upstream-gone) across one or many repos,
    safely and with a dry-run.
---

# Git Cleanup

After a PR merges and its remote branch is deleted, the local branch stays behind
and shows as `[gone]` in `git branch -vv`. This skill removes exactly those — no
current branch, no branch with unmerged work git doesn't consider gone.

The heavy lifting is in [`scripts/cleanup.sh`](scripts/cleanup.sh); this file is the
routing and safety contract.

---

## Resolving which repos to clean

In priority order:

1. **Explicit path argument** — `/git-cleanup /path/to/repo` cleans just that repo.
2. **The projects-db roster** — with no argument, read the machine-local
   `projects-db.md` (maintained by the `projects-db` skill) and clean each repo's
   `path`. This is the multi-repo default.
3. **`REPO_PATHS` environment variable** — a fallback when there's no roster: a
   path-list (OS path separator) of repo roots to clean.
4. **Prompt the user** — if none of the above resolve any path, ask which repo(s)
   to clean. Never guess a path.

Never hardcode repository paths in this skill or its script — they are always
resolved at runtime from one of the sources above.

---

## Running it

```bash
# Preview only — lists what would be deleted, deletes nothing
bash scripts/cleanup.sh /path/to/repo --dry-run

# Actually prune the gone branches in one repo
bash scripts/cleanup.sh /path/to/repo

# Multi-repo: iterate the roster's paths, dry-run first
```

Always **dry-run first** when cleaning more than one repo or an unfamiliar one, show
the user the list, and only then run for real.

---

## Safety contract

The script deletes a branch **only** when git itself marks its upstream as `: gone]`
in `git branch -vv`. It:

- **never** touches the currently checked-out branch (the `*` line);
- **never** deletes a branch whose upstream still exists;
- uses `git branch -D` only on the gone set — but you should still dry-run to confirm the set looks right before a bulk run;
- exits 0 on a clean run (including "nothing to prune"), non-zero only on a real error.

`[gone]` means the remote branch was deleted, which normally means the PR merged.
If you kept local-only work on such a branch that was never pushed, that work would
be lost — the dry-run is your check against that. When in doubt, show the list and
confirm before deleting.

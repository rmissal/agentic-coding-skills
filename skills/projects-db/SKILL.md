---
name: projects-db
description: >-
  Use this skill to manage the machine-local roster of repositories you work in — the projects-db.md file that lets the other skills operate across many repos. Onboard a new repo (auto-detect its language, default branch, and which of its own standard docs hold its context), list the onboarded repos, refresh a stale entry, or resolve a project name to its path and context docs. Trigger it when the user says "onboard this repo", "add my project", "which projects do I have", "where is <project>", or when another skill needs a repo path and the roster is empty. The roster stores pointers only — per-repo context is always read from that repo's own README / ARCHITECTURE / CLAUDE / CONTRIBUTING, never copied here. Do NOT use it to store secrets, absolute-path secrets, or architecture notes.
user-invocable: true
metadata:
  domain: >-
    Maintaining the machine-local multi-repo roster (projects-db.md) of pointers —
    path, language, branch, and which of each repo's own docs hold its context.
---

# Projects DB

The machine-local index that makes the library multi-project. `projects-db.md`
(gitignored) is a roster of the repos you work in — **pointers only**. Per-repo
context is never stored here; it's read on demand from each repo's own standard
docs. This mirrors the `coding` skill's repo-discovery order and keeps a single
source of truth for each repo's context (the repo itself).

The file lives at the repo root, created from `projects-db.md.example` by setup or
by `onboard`. If it's missing when any action runs, create it from the example
first.

---

## Roster shape

A markdown table, one row per repo:

| name | path | language | default branch | context docs |
|---|---|---|---|---|
| example-service | /path/to/example-service | TypeScript | main | README.md, ARCHITECTURE.md |

- **name** — short handle; defaults to the directory name.
- **path** — absolute path to the repo root on this machine.
- **language** — primary language, auto-detected.
- **default branch** — from git.
- **context docs** — which of the repo's *own* standard docs exist (README.md /
  ARCHITECTURE.md / CLAUDE.md / CONTRIBUTING.md). Skills open these directly.

---

## Actions

### `onboard <path>` — add a repo
Profile the repo and append a row. Use the helper for deterministic detection:

```bash
bash skills/projects-db/scripts/profile_repo.sh /path/to/repo
```

It prints the tab-separated fields `name  path  language  default-branch  context-docs`.
Detection rules:
- **language** — from lockfiles/manifests (`package.json`→JS/TS, `pyproject.toml`/`requirements.txt`→Python, `go.mod`→Go, `Cargo.toml`→Rust, `pom.xml`/`build.gradle`→Java; falls back to the most common source extension).
- **default branch** — `git symbolic-ref refs/remotes/origin/HEAD` (falls back to the current branch).
- **context docs** — presence check for README.md / ARCHITECTURE.md / CLAUDE.md / CONTRIBUTING.md (and `docs/architecture.md`).

Append the row to `projects-db.md`. Don't duplicate an existing path — if the path
is already listed, treat it as a `refresh` instead.

### `list` — show the roster
Read `projects-db.md` and present the table. If empty, say so and offer to onboard.

### `refresh [<name|path>]` — re-profile
Re-run detection for one repo (or all, if no argument) and update its row. Use after
a repo changes language, adds a context doc, or renames its default branch.

### `where <name>` — resolve a project
Given a project name (or fuzzy match), return its path and its context docs, then
**read those docs from the repo itself** to answer whatever the caller needs. This
is the bridge other skills use: resolve → open the repo's own README/ARCHITECTURE,
never a copy stored here.

---

## Hard rules

- **Pointers, not content.** Never paste architecture notes, API details, or
  per-repo context into `projects-db.md`. Store the pointer (which doc has it) and
  read the doc on demand.
- **Never create a competing per-repo context file.** A repo's context lives in its
  own README / ARCHITECTURE / CLAUDE / CONTRIBUTING. If a repo lacks these, suggest
  the user add them to that repo — don't invent a sidecar file this skill owns.
- **No secrets, no secret paths.** The roster is machine-local and gitignored, but
  still holds only non-sensitive pointers. Credentials belong in the agent's secret
  store, never here.
- **Absolute paths stay machine-local.** `projects-db.md` is gitignored precisely
  because it contains absolute paths; never commit it or echo its paths into a
  committed file.

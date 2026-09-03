---
name: coding
description: >-
  Use this skill when writing, editing, or reviewing code — across any language (Python, TypeScript, Go, Rust, Java, YAML, shell, Gherkin, and more). Covers repo discovery (reading CLAUDE.md, README, CONTRIBUTING/ARCHITECTURE, CI workflows, and formatter/linter config to learn a repo's specific rules before touching anything), code review for design flaws (SOLID, DRY, KISS, YAGNI, separation of concerns), reviewing AI-generated diffs for hallucinated APIs and silent scope creep, proposing edits with justification, writing or fixing tests, authoring new code, refactoring, assessing style violations, and safe git workflow (branch + PR, never push to main). Discovers and runs the repo's own pinned formatters and linters rather than assuming a toolchain. Do NOT use for creating or editing skills — use skill-creator for that.
user-invocable: false
metadata:
  domain: >-
    Writing, editing, and reviewing production code in any language, grounded in
    each repo's own discovered conventions.
---

# Coding

Language-agnostic engineering discipline. It applies to whatever the repo under
your hands actually uses — the first job is always to discover that, not to assume it.

---

## Repo Discovery — do this first in any unfamiliar repo

Before writing or reviewing any code, learn what the specific repo is about. Every
repo has its own toolchain, conventions, and constraints that override general
defaults. Never assume — discover.

Read in this order (all can be done in parallel):

1. **CLAUDE.md files** — highest priority; explicit human-authored rules that override everything else
   ```bash
   find . -name "CLAUDE.md" -not -path "*/node_modules/*" | xargs cat 2>/dev/null
   ```
2. **README.md** — purpose, architecture overview, quick-start, known constraints
3. **CONTRIBUTING.md / ARCHITECTURE.md / docs/architecture.md** — coding standards, layering rules, PR checklists, naming conventions
4. **CI workflows** — the authoritative list of what must pass before merge
   ```bash
   ls .github/workflows/ 2>/dev/null && grep -h "run:\|uses:" .github/workflows/*.yml 2>/dev/null | head -40
   ```
5. **Formatter/linter config** — `pyproject.toml`, `ruff.toml`, `.eslintrc*`, `.prettierrc*`, `Makefile`, `go.mod`, `Cargo.toml` — tells you the exact flags and rules the repo enforces
6. **`package.json` scripts / `Makefile` targets** — often a single `make lint` or `npm run ci` wraps everything; prefer running that over reconstructing individual commands

From this, build a mental model: *What does this repo do? What language/framework?
What formatter and with what flags? What test runner? What CI jobs must pass? Are
there repo-specific patterns or forbidden practices?*

A rule found in CLAUDE.md or CI beats a general best practice. When a repo pins a
formatter version or line length, use exactly that — never a global default.

---

## Edit Workflow

Follow this sequence for any code change, regardless of repo or language.

1. **Run Repo Discovery above** if you haven't already this session — binding rules from CLAUDE.md, CONTRIBUTING.md, and CI override general defaults. Don't skip even if you think you know the codebase.
2. **Read** the file(s) to change — never propose edits blind.
3. **Read** the associated tests — if none exist, plan to create them.
4. **Propose** the implementation change — show a clear before/after, explain *why* it's correct.
5. **Propose** the test change — every implementation change ships with a test change; no exceptions.
6. **Confirm** with the user — wait for explicit approval before touching anything.
7. **Branch + push** — create a feature branch, push commits there (see Git Workflow below).
8. **Open a PR** targeting the default branch with a summary and test plan (see the `finalize-and-open-pr` skill).

---

## Reviewing AI-generated code

The bottleneck has shifted from *writing* code to *reviewing* it. When the diff under
review was produced by an AI — your own first draft, or another agent's — apply the
same rigor you'd give a human PR, plus the failure modes specific to generated code:

- **Hallucinated APIs** — a function, flag, import, or config key that reads plausibly but doesn't exist. Grep the repo for it before trusting it.
- **Silent scope creep** — edits beyond the task (a "helpful" refactor, a renamed symbol, an unrelated touched file). Confirm every hunk maps to the stated requirement; drop the rest.
- **Tests that assert nothing** — a test green because it never exercises the change.
- **Fixture-vs-production mismatch** — mock/sample data drifted from the real data shape, so the test passes but validates nothing.
- **Plausible-but-wrong reasoning** — a confident comment or commit message that misdescribes what the code does. Read the code, not the narration.

A fluent diff is not a correct one. Reviewing is the work — do not rubber-stamp
generated output.

---

## SOLID

### S — Single Responsibility
One function / class / module does exactly one thing. If you need "and" to describe it, split it.

```python
# Bad
def fetch_and_save_results(run_id, output_path): ...
# Good
def fetch_results(run_id): ...
def save_results(results, output_path): ...
```

### O — Open/Closed
Extend by adding new code, not by editing existing code. Add a new handler/plugin
rather than growing an existing function with more `if:` branches.

### L — Liskov Substitution
Any subclass must be usable in place of its parent without breaking the caller.
Practically: avoid subclassing unless the IS-A relationship is obvious. Prefer composition.

### I — Interface Segregation
Callers should not depend on interfaces they don't use. Don't pass a large config
dict to a function that only needs two keys — pass those two keys.

### D — Dependency Inversion
High-level logic should not instantiate its own dependencies. Pass them in.

```python
# Bad — hardwired dependency
def run():
    client = ApiClient(token=os.getenv("API_TOKEN"))

# Good — injected; main() owns os.getenv, nothing else does
def run(client: ApiClient): ...
def main():
    run(client=ApiClient(token=os.getenv("API_TOKEN")))
```

---

## Universal Principles

### DRY — Don't Repeat Yourself
Every piece of knowledge has one authoritative source. Extract repeated logic into
helpers, repeated test setup into fixtures, repeated build steps into shared actions.

### KISS — Keep It Simple
The simplest solution that handles the real cases is the right one. Complexity must justify itself.

### YAGNI — You Aren't Gonna Need It
No "might want later" abstractions, no optional parameters with no current caller,
no framework-style base classes for a single concrete use case.

### Law of Demeter
A function should only call methods on its own arguments, objects it created, or its
direct instance variables. Long chains (`a.b.c.d.method()`) are a fragility smell.

### Separation of Concerns
I/O, business logic, and configuration belong in separate layers.

### Command-Query Separation
A function either **does something** (command — side effects, no return value) or
**returns something** (query — no side effects). Not both.

### Fail Fast
Validate at entry points. Raise early with a clear message.

```python
def process(run_id: str):
    if not run_id:
        raise ValueError("run_id is required")
```

### Verifiable Success Criteria
Before writing code, state concrete checkable outcomes and how you'll verify them.
If you can't describe how to verify the change is correct, you don't yet understand the problem.

### Don't Abort on Already-Effective Side Effects
Once a step has produced a visible external effect (PR opened, branch pushed, file
written), a later failure should warn and continue — not abort as if nothing happened.

```python
# Bad — PR is live on the remote but run goes red
create_pr(...)
enable_auto_merge(...)  # raises → caller thinks nothing was created

# Good
create_pr(...)
try:
    enable_auto_merge(...)
except RuntimeError as exc:
    log.warning("auto-merge could not be enabled: %s — PR is live, merge manually", exc)
```

---

## Git Workflow

### Never push directly to the default branch
All changes go through a branch + PR, regardless of how small or obvious the fix is.
Direct pushes bypass CI and peer review — including follow-up chores identified during
a review.

1. Create a branch from the default branch → feature/fix branch name
2. Commit changes to that branch
3. Open a PR against the default branch (see the `finalize-and-open-pr` skill)

---

## Per-language style

Discover the repo's pinned config first; the notes below are defaults for when the
repo says nothing.

### Python
- `snake_case` functions/variables, `PascalCase` classes, `UPPER_CASE` module constants; two blank lines between top-level defs (PEP 8).
- Explicit over implicit: no `from module import *`, no silent `except: pass`.
- Type hints on all signatures (`def fetch(run_id: str, top: int = 10) -> list[dict]: ...`).
- Prefer pure functions — output depends only on inputs; move `os.getenv` to `main()` and pass resolved values down.
- Composition over inheritance.
- **Run the repo's pinned formatter/linter** (black/ruff/isort/autoflake, etc.) with the repo's flags before committing. If the repo pins a line length or version, use exactly that — never a global default (a wrong line length reformats files in a way CI rejects).

### Python test style (pytest-native)
When the repo uses pytest, write **pytest-native** tests, not `unittest.TestCase`:
- Plain `class TestX:` or module-level `test_*` functions — no `TestCase` base. Keep a class grouping when a module reuses `test_*` method names across classes.
- Plain `assert` (`assert a == b`, `assert x in y`, `assert x is None`), never `self.assertEqual/assertIn/...`.
- `with pytest.raises(E) as e:` instead of `self.assertRaises`; the bound var's `.exception` becomes `.value`.
- `setUp`/`tearDown` → `@pytest.fixture(autouse=True)` that `yield`s. Prefer built-in fixtures: `tmp_path` over `tempfile.mkdtemp()`, `monkeypatch` over manual env save/restore, `capsys` over redirecting `sys.stdout`.
- `@pytest.mark.parametrize` over `subTest(...)` loops.
- Shared fixtures + factory helpers in `conftest.py`.
- `from unittest.mock import patch, MagicMock` is fine — that's the mock library, unrelated to runner style.

### YAML
- Run the repo's `yamllint` config if present. Typical relaxations: allow `on:` as a key (`truthy: {check-keys: false}`), disable `document-start`, generous `line-length` for CI-expression lines.

### TypeScript / Playwright
- Prefer `async/await` over Promise chains.
- Keep selector logic in Page Object classes — no inline `page.locator()` in specs.
- No hardcoded waits (`waitForTimeout`); use `waitForSelector`, `waitForResponse`, or auto-waiting.

### Gherkin / Cucumber
- One behavior per scenario — a title containing "and" is likely two scenarios.
- Steps describe intent, not implementation (`When I submit the form`, not `When I click the submit button`).
- No `if`/`for`/`switch` in step definitions — logic belongs in helpers or Page Objects.

### Shell
- Quote variables (`"$VAR"`, not `$VAR`); `set -euo pipefail` or explicit error handling; never `rm -rf` on an unquoted path.

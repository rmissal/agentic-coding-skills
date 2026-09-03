---
name: test-quality
description: >-
  Use this skill when writing, reviewing, or judging the quality of tests — unit, integration, or end-to-end, in any language or framework. Enforces the validate-before-assert instinct (a test must actually exercise the change and prove the real behavior, not pass vacuously), scopes effort with a SMOKE / STANDARD / FULL rigor ladder so you don't over- or under-test, and triages failures by cause (real defect vs flaky vs environment vs bad test) instead of blindly re-running or deleting. Catches the failure modes that make a green suite lie: tests that assert nothing, fixtures drifted from production data, mocked-away behavior under test, and reproductions that never hit the real system. Do NOT use for authoring production (non-test) code — use the coding skill for that.
user-invocable: false
metadata:
  domain: >-
    Judging and improving test quality — that tests exercise real behavior, are
    scoped to the right rigor, and fail for real reasons.
---

# Test Quality

A green suite that proves nothing is worse than no suite — it manufactures false
confidence. This skill is the instinct for tests that actually validate.

---

## Validate before you assert

Before writing an assertion, answer: *what real behavior am I proving, and would
this test fail if that behavior broke?* If you can't answer, the test is theater.

The failure modes that make a suite lie:

- **Asserts nothing.** The test runs the code but never checks a meaningful result — or asserts on a constant it set itself. It's green because it can't be red.
- **Mocks away the behavior under test.** You stubbed the exact function you meant to verify, so the test proves the mock returns what you told it to.
- **Fixture drift.** Sample/mock data no longer matches the real data shape. The test passes against a fiction; production breaks.
- **Never hits the real system.** An "integration" test that only exercises in-process fakes proves integration with nothing. At least one test in the ladder must run against the real system under test.
- **Tests the framework, not the code.** Verifying that a library does what its docs say adds no signal about *your* change.

The check: could this test **only** pass if the intended behavior is present? If a
trivially broken implementation would still pass, the test is wrong.

---

## Rigor ladder — scope effort to risk

Not every change needs the full suite; not every change is safe with a smoke test.
Pick the rung deliberately.

### SMOKE — "does it run at all?"
A handful of the happiest paths against the real system under test. Fast, shallow,
catches gross breakage (won't start, obvious wiring error). Use for: trivial changes,
a quick reachability check before deeper work, or confirming the environment is sane.
**Not sufficient to merge non-trivial behavior.**

### STANDARD — "does the change work, including its edges?"
The changed behavior plus its edge cases and error paths, with real dependencies
where they matter and mocks only at true boundaries. This is the default for a normal
feature or fix. Every behavior change ships at this rung minimum.

### FULL — "does the whole thing still work end-to-end?"
The complete suite, including slow/expensive/e2e tests against the real system. Use
for: risky or cross-cutting changes, release gates, refactors that touch shared code,
or anything where a regression elsewhere is plausible.

Escalate a rung when: the change touches shared/critical code, you're near a release,
or a SMOKE/STANDARD run surfaced something surprising.

---

## Failure triage — diagnose before you react

A failing test is data, not an obstacle. Never blindly re-run until green, and never
delete or `skip` a failing test to make the suite pass. Classify first:

| Cause | Signal | Right action |
|---|---|---|
| **Real defect** | Fails deterministically; the assertion describes correct behavior the code now violates | Fix the code. The test did its job. |
| **Bad/outdated test** | The behavior is intentionally different now; the test encodes a stale expectation | Update the test to the new correct behavior — and confirm the new behavior is actually intended, not an accidental change. |
| **Flaky** | Passes/fails non-deterministically on re-run with no code change | Find the root cause (timing, ordering, shared state, real network). Fix the flakiness — don't paper over it with retries. |
| **Environment** | Fails only here — missing dependency, credential, service, or data the test assumes | Fix the environment or make the test's precondition explicit (skip-with-reason if the dependency is genuinely absent). Don't claim a pass you didn't get. |

When you report results, name the cause. "3 failures: 1 real defect (fixed), 2
environment (missing local service)" is useful; "some tests failed, re-running" is not.

---

## When reviewing someone else's (or an AI's) tests

Apply the same lens to a diff's tests as to its code:
- Does each new test map to a behavior in the change? A test with no corresponding behavior is noise.
- Remove the assertion and confirm the test would then fail — if it still passes, it asserts nothing.
- Check fixtures against the real data shape, not against what's convenient.
- A PR that changes behavior but touches no tests is incomplete — send it back.

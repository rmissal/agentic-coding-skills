---
name: requirements-engineering
description: >-
  Use this skill BEFORE building anything non-trivial — when the ask is vague, underspecified, or could reasonably be interpreted several ways, or when you're about to write code, a test, a script, or a config change and haven't nailed down exactly what "done" means. Turns a loose request into a verifiable specification through two phases: (A) reflect and challenge — restate the goal, surface hidden assumptions, list open questions, and push back on scope; (B) write a concise spec — problem, non-goals, target environment/system, inputs/outputs, acceptance criteria, and how each will be verified. Prevents building the wrong thing, which is now the most expensive failure mode. Do NOT use for trivial one-line changes where the requirement is already unambiguous.
user-invocable: true
metadata:
  domain: >-
    Converting a vague or underspecified request into a verifiable specification
    before any implementation begins.
---

# Requirements Engineering

Writing code is cheap; building the wrong thing is expensive. Reviewing and
verifying is now the bottleneck — so spend one focused round up front turning a
loose ask into a spec you can check against. Do this *before* touching code.

Two phases. Don't skip Phase A — the challenge round is where wrong assumptions die.

---

## Phase A — Reflect & Challenge

Before proposing any solution, do this thinking out loud (briefly):

1. **Restate the goal** in one sentence, in your own words. If you can't, you don't understand it yet — ask.
2. **Surface hidden assumptions.** What are you taking for granted about the environment, the data, the users, the existing code, the "obvious" interpretation? List them explicitly.
3. **List open questions.** Anything with more than one reasonable answer is an open question, not a decision you get to make silently.
4. **Challenge the scope.** Is the whole ask necessary? Is there a smaller change that delivers the real value (YAGNI)? Is the request solving a symptom rather than the cause? Push back when the framing looks wrong — that's the point of this phase.
5. **Identify the target system.** What environment / system / repo / service is this actually for? Its real constraints (runtime, data shape, integrations, existing conventions) drive the spec far more than the abstract request does.

Resolve the open questions with the user *now* — a two-minute clarification beats a
day building the wrong thing. Use crisp either/or questions, not open-ended ones.

---

## Phase B — Write the Spec

Once Phase A settles, write a short, concrete spec. Keep it tight — a spec that
takes longer to read than the change takes to build is over-engineered.

```markdown
## Problem
<one paragraph: what's wrong / missing, and why it matters>

## Goal
<one sentence: the outcome that makes this done>

## Non-goals
<what this explicitly does NOT do — the scope fence>

## Target system
<the environment / repo / service this lands in, and its binding constraints>

## Inputs → Outputs
<what goes in, what comes out; data shapes, formats, edge cases>

## Acceptance criteria
- [ ] <concrete, checkable outcome 1> — verified by <how>
- [ ] <concrete, checkable outcome 2> — verified by <how>
- [ ] ...
```

Every acceptance criterion must be **verifiable**: paired with a concrete way to
check it (a test, a command, an observable behavior). "It should work" is not a
criterion. "Running `<cmd>` exits 0 and prints N rows" is.

---

## Worked example

**Vague ask:** *"Add caching so the report page is faster."*

**Phase A output:**
- *Goal restated:* reduce report-page load time by avoiding repeated expensive recomputation.
- *Assumptions to check:* the slowness is recomputation (not network / rendering)? the underlying data changes rarely enough that a cache is even correct? there's a single hot path or many?
- *Open questions:* acceptable staleness window? per-user or global cache? in-memory (dies on restart) or persistent? what's the current p95 load time and the target?
- *Scope challenge:* is caching the right fix, or is the query itself unindexed? Measure first — a missing index may beat a cache with none of the staleness risk.

**Phase B spec (after the questions are answered):**
- **Problem:** report page recomputes an aggregate on every request; p95 is 4.2s.
- **Goal:** p95 under 800ms for the report page.
- **Non-goals:** no change to the aggregate's correctness; no new infrastructure.
- **Target system:** the reporting service; aggregate is pure over its inputs; data refreshes hourly.
- **Inputs → Outputs:** same request in, same aggregate out, served from a 60-min TTL cache keyed on the report parameters.
- **Acceptance criteria:**
  - [ ] p95 load time < 800ms — verified by load test before/after.
  - [ ] Stale data never exceeds 60 min — verified by a TTL-expiry unit test.
  - [ ] Cache miss path returns identical output to the pre-change code — verified by a golden-output test.

---

## Token discipline

This skill is a *thinking* investment, not a writing marathon. Phase A is a few
bullet points, Phase B is one short template. If the spec balloons past the size of
the change it describes, you're over-specifying — cut it back to the criteria that
actually gate "done".

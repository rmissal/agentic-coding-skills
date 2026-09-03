---
name: agent-output-eval
description: >-
  Use this skill to systematically evaluate the quality of agent or skill output — when you need to judge whether an AI's answer, a skill's behavior, or a generated artifact meets a bar, and especially when checking many cases at once. Provides a repeatable harness: define evaluation cases (prompt + expected qualities + rubric), run them in parallel as independent evaluators, score each PASS / PARTIAL / FAIL / SKIP against explicit criteria, and roll up a summary table so regressions and weak spots are visible at a glance. The framework is domain-neutral — the adopting project supplies its own cases. Do NOT use to grade skill trigger descriptions specifically (use grade-skills) or to validate YAML frontmatter (use the frontmatter validator).
user-invocable: false
metadata:
  domain: >-
    A domain-neutral harness for evaluating agent/skill output quality against
    explicit per-case rubrics, scored and rolled up.
---

# Agent Output Eval

A harness for judging output quality repeatably. It answers "is this good enough,
and where is it weak?" with evidence, not vibes. The framework is generic — you
bring the cases.

---

## The model

An **evaluation case** is a self-contained judgment:

- **Prompt / input** — what the agent or skill was asked to do.
- **Expected qualities** — the observable properties a good output has (not a single golden string; a set of criteria).
- **Rubric** — how to score against those qualities.

Cases are **independent**, so a batch runs as parallel evaluators — each one judges
one case with no shared state — and the results roll up into one table. Independence
is what makes the harness scale and keeps one case's verdict from biasing another's.

---

## Scoring rubric

Score every case on this four-value scale. Four values, not a percentage — a coarse,
honest verdict beats a falsely precise number.

| Verdict | Meaning |
|---|---|
| **PASS** | Meets all expected qualities. No material gap. |
| **PARTIAL** | Meets the core intent but misses a quality, or is right with a caveat. Usable, not clean. |
| **FAIL** | Misses the core intent, is wrong, or violates a hard constraint. |
| **SKIP** | Could not be evaluated (missing dependency, precondition, or the case doesn't apply here). Never silently count a SKIP as a PASS. |

For PARTIAL and FAIL, record *why* in one line — the specific quality that missed.
The reason is the actionable part; the verdict alone isn't.

---

## Running a batch

1. **Collect the cases** — from the adopting project's `evals/` (see the case template below). Each project supplies cases relevant to its own agents/skills.
2. **Run evaluators in parallel** — one per case, independent, in the background where the harness allows. Each produces a `{verdict, reason}` for its case.
3. **Roll up** into a summary table, most-severe first, so FAILs and PARTIALs surface before PASSes.

```
Case            Verdict   Reason
--------------- --------- ------------------------------------------
CASE-03         FAIL      hallucinated a config key that doesn't exist
CASE-07         PARTIAL   correct answer, omitted the error-path caveat
CASE-01         PASS      —
CASE-02         PASS      —
CASE-05         SKIP      requires a live service not available here
--------------- --------- ------------------------------------------
Totals: 2 PASS · 1 PARTIAL · 1 FAIL · 1 SKIP
```

4. **Read the failures, not the score.** The value is in the reasons — they tell you what to fix. A "2/5 PASS" headline is useless without them.

---

## Case template

Adopting projects define cases in this shape (`evals/cases.json`, or inline):

```json
{
  "id": "CASE-01",
  "prompt": "<the input given to the agent/skill under test>",
  "expected_qualities": [
    "<observable property a good output has>",
    "<another>"
  ],
  "rubric": "<how to decide PASS/PARTIAL/FAIL for this case>",
  "notes": "<optional: known edge cases, why this case exists>"
}
```

Keep `expected_qualities` observable and checkable. "Answer is helpful" is not a
quality; "names the specific file that must change and why" is.

---

## Generic illustrative cases

Two examples showing the shape; replace with your own domain's cases.

```json
[
  {
    "id": "GEN-CODEFIX",
    "prompt": "A test is failing with a null-pointer error on line 42. Fix it.",
    "expected_qualities": [
      "identifies the actual root cause, not just the symptom line",
      "the fix handles the null case rather than suppressing the error",
      "adds or updates a test that would fail without the fix"
    ],
    "rubric": "PASS if all three; PARTIAL if the fix is correct but adds no test; FAIL if it only silences the error (e.g. broad try/except) or edits the test to pass without fixing the code."
  },
  {
    "id": "GEN-AMBIGUOUS-ASK",
    "prompt": "Make the export faster.",
    "expected_qualities": [
      "surfaces the ambiguity (which export? current baseline? target?) before building",
      "does not silently pick one interpretation and implement it"
    ],
    "rubric": "PASS if it clarifies scope first; PARTIAL if it states an assumption explicitly then proceeds; FAIL if it builds a full solution against an unstated guess."
  }
]
```

> **Adopting projects supply their own cases.** This skill ships only the harness
> and the template — the cases live with the agents/skills they evaluate.

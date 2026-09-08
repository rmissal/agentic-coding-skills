---
name: project-management
description: >-
  Use this skill to govern and steer software projects across their lifecycle — defining and defending MVP boundaries, breaking initiatives into prioritized milestones and sprints, tracking multi-track or multi-developer task assignments, synchronizing project state across standard artifacts (ROADMAP.md, architecture docs, CHANGELOG.md), and enforcing go-live readiness gates. Trigger when users ask to plan a project, define an MVP, organize a roadmap, start or review a sprint, triage new features to prevent scope-creep, track progress across development tracks, or prepare a release checklist.
user-invocable: true
metadata:
  domain: >-
    Governing project lifecycle, milestone roadmaps, sprint execution, and artifact synchronization.
---

# Project Management

Writing code without continuous steering leads to scope bloat, delayed launches, and documentation that drifts from reality. This skill provides the operational playbook to drive software initiatives from initial concept to a validated production release.

It operates across five disciplined phases:

---

## Phase 1 — MVP Scoping & The Anti-Scope-Creep Fence

The primary risk of any early-stage software project is trying to ship the ultimate vision on day one. When defining or reviewing an MVP (Minimum Viable Product):

### 1. Identify the Closed Value Loop
Define the single smallest end-to-end loop that delivers standalone value to the user:
```
[Trigger / Entry] ──> [Core Action / Transformation] ──> [Feedback / Result] ──> [State Preserved]
```
If a feature does not directly serve this loop, it does not belong in MVP 1.

### 2. Ruthless In-vs-Out Triage
Classify every candidate feature into a concrete boundary table:

| Domain | In Scope for First Go-Live (MVP 1) | Out of Scope (Parked for MVP 2+) |
|---|---|---|
| **Core Workflow** | The indispensable happy path. | Edge-case automations, alternative flows. |
| **Data & Storage** | Simplest viable persistence (e.g., local-first / offline). | Complex multi-device cloud sync, conflict resolution. |
| **Integrations** | Core external APIs essential for the primary promise. | Secondary third-party plugins, export tools. |
| **User Management**| Anonymous or local device profiles. | Full multi-tenant authentication, SSO, social login. |

### 3. Reject the Three Premature Traps
- **Premature Cloud Infrastructure:** If a product can be validated locally or offline-first, avoid standing up distributed databases and authentication services that introduce regulatory liabilities and hosting costs before product-market fit.
- **Premature Hardware / Platform Variants:** Validate on the primary platform/device form factor before attempting multi-platform or fragmented peripheral support.
- **Premature Regulatory / High-Risk Exposure:** Position early AI or automated capabilities as formative guidance rather than summative or high-stakes evaluation to avoid triggering heavy compliance certifications prematurely.

---

## Phase 2 — Roadmap Structuring & Track Segregation

Never mix user-facing product features with foundational engineering work in a single unorganized list. Always segregate roadmaps into two distinct, parallel tracks:

### 1. Feature Roadmap (User & Product Value)
- Organizes deliverables by user milestones and visible capability improvements.
- Uses user-centric definitions of done (e.g., "Student can input semester grades and view weighted GPA").

### 2. Architecture Roadmap (Technical & System Foundation)
- Tracks technical health, data models, non-functional requirements, security, and compliance.
- Organizes deliverables by technical pillars (e.g., Modularization, Persistence, Safety Guardrails, Telemetry).

### 3. Explicit Milestone Tagging
Every backlog item must be tagged with its target horizon:
- `[MVP 1]` — Required to unlock the first public/internal release.
- `[MVP 2]` — First fast-follow iteration based on initial user feedback.
- `[Future / Parked]` — Deprioritized ideas preserved for long-term vision.

---

## Phase 3 — Multi-Track Sprint Orchestration

When multiple contributors, subagents, or workstreams operate on a codebase, uncoordinated edits create merge conflicts and blocked dependencies.

### 1. Decouple Streams by Bounded Context
Assign parallel workstreams to isolated architectural layers or feature packages:
- **Track A (e.g., Data / Core Engine):** Focuses on schema entities, repositories, calculations, and domain logic.
- **Track B (e.g., UI / Presentation / Interaction):** Focuses on screens, design system tokens, sound/haptics, and visual components.

### 2. Work-in-Progress (WIP) Limits
Enforce strict focus: **maximum 1 active task per track/contributor** at any time. Do not begin a new task while the active task remains unverified.

### 3. Standard Task Lifecycle
Move tasks through explicit states in sprint tables:
`[Backlog]` ──> `[In Progress]` ──> `[Blocked]` ──> `[Done]`

---

## Phase 4 — The Atomic Artifact Sync Protocol

Software documentation rots when code changes are made without updating project artifacts. Whenever a task is completed, update the following three artifacts in the **same atomic commit**:

1. **`ROADMAP.md`**:
   - Mark the item as `[x] Done`.
   - Update the active sprint table status.
2. **Project Architecture / State Docs** (e.g., `README.md`, `ARCHITECTURE.md`, or state summaries):
   - Update verified components and active priorities.
3. **`CHANGELOG.md`**:
   - Add a dated entry detailing what changed, the rationale, and any architectural impact.

**Rule:** An implementation is never "Done" if the project roadmap and changelog have not been updated.

---

## Phase 5 — Go-Live & Release Readiness Gates

Before cutting a release candidate or publishing to an app store/production environment, enforce three non-negotiable readiness gates:

### 1. Technical Verification Gate
- Clean build across all target build variants.
- Zero static analysis or linter errors (`0 errors`).
- 100% passing automated test suite (unit + integration).

### 2. Platform & Regulatory Policy Gate
- Target audience declarations and age-group classifications configured.
- Privacy policy hosted, accurate, and aligned with actual data transmission practices.
- Mandatory transparency labels displayed (e.g., AI-generated content disclosures).
- Data subject rights supported (e.g., local data wipe / right to erasure).

### 3. Staged Rollout Gate
- Deploy to an internal/closed testing track first.
- Complete smoke testing on real target devices.
- Review error/crash logs before expanding to production.

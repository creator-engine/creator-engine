# CE v3 — Stage Vocabulary (canon)

*Canon decision + dual-mapping reference (provenance: 2026-06-07 design session; GH #159). **CANON — terminology-canon-tracked.** The user-facing cognitive phases are a presentation layer over the conserved mechanical state machine; this document is the authority for both and their correspondence. Execution status lives in [`docs/v3-roadmap.md`](../v3-roadmap.md).*

## The decision

CE presents users a clear, intuitive, **fractal** cognitive-phase vocabulary for "what am I doing right now," while **conserving the existing mechanical state machine underneath**. The vocabulary is CE canon — a peer to **Operator** and **Controller** — and surfaces in the `ce session` status line, the ◆ CE Completion Report, the board, and these docs.

**The canon lexicon (locked 2026-06-07):**

> **Frame → Shape → Build → Review → Ship**

- **Frame** — understand and bound the problem/ticket: what is being asked, why, and what "done" means.
- **Shape** — turn the framed problem into a ratifiable bet: acceptance criteria, appetite (a fixed effort budget, not an estimate), mutation class, and the plan. Ends when the bet is placed (ratified) and the work is Ready.
- **Build** — execute the ratified bet in one governed, boxed run.
- **Review** — grade the result against the acceptance criteria (external grading; evidence, not transcripts).
- **Ship** — the governed terminal delivery: a merged PR, delivered research, or a ratified no-change.

### Conserve the machine (load-bearing principle)

The cognitive vocabulary is a **skin**. The precise mechanical state machine remains the **engine / board / evidence** layer where governance lives, and is **conserved verbatim** — this canon renames or removes **zero** enums. The skin sits over the machine and maps to it; it never replaces or hides it. A curious user can always "dig in" to the machine under the skin (see [The conserved machine](#the-conserved-machine-dig-in-layer)).

## The dual mapping (the core artifact)

User-facing cognitive phase ↔ board/pipeline label ↔ mechanical spec-lifecycle state ↔ gate ↔ BMAD phase:

| Cognitive phase | Board label | Spec-lifecycle state | Gate | BMAD phase |
| --- | --- | --- | --- | --- |
| **Frame** | `BACKLOG` | `draft` | — | Analysis |
| **Shape** | `SHAPE → READY` | `draft → ready` | **front gate:** Definition-of-Ready (scope + `acceptance_criteria` + verification) **+** bet-ratification ("place the bet") | Planning + Solutioning |
| **Build** | `RUN` | `in_progress` | *(container lifecycle: `provision → run → collect → teardown`)* | Implementation |
| **Review** | `REVIEW` | `verified` | external grading (review-evidence; **non-ratifying**) | — *(CE first-class tail)* |
| **Ship** | `MERGE` | `ratified → done` | **back gate:** final ratification (mutation_class-tiered) **+** governed merge | — *(CE first-class tail)* |

Notes:

- **`Shape` is deliberately overloaded.** It is both a cognitive phase and (as `SHAPE`) one of the board states it subsumes. The user-facing `Shape` spans board `SHAPE → READY` plus the DoR gate: the dominant phase keeps its name.
- **The two-end gate chain is where governance binds.** The **front gate** (Shape→Build) is the Definition-of-Ready plus the bet; the **back gate** (at Ship) is the `mutation_class`-tiered ratification plus the branch-protection-enforced merge. `Build` and `Review` are the middle.

## The conserved machine (dig-in layer)

These are the mechanical enums the skin rides on — **conserved, not renamed by this canon:**

- **Spec lifecycle (6 states):** `draft → ready → in_progress → verified → ratified → done` — `schemas/spec-wrapper-sidecar.schema.yaml` (`status`, Feature 001 FR-013a).
- **Container lifecycle phase (4):** `provision → run → collect → teardown` — `schemas/runtime-evidence.schema.yaml` (`lifecycle_phase`).
- **Terminal run-outcome (5):** `pr_opened · pr_merged · review_submitted · research_delivered · no_change` — `schemas/runtime-evidence.schema.yaml:247` (`outcome`; orthogonal to `lifecycle_phase`).
- **Mutation class (risk tier):** `docs · code · schema · deploy · governance · identity · security · attestation · redaction` (+ `none`) — `schemas/mutation-class.schema.yaml`; drives the back gate.
- **The 25-state SDLC operating model** — `docs/architecture/agentic-sdlc-operating-model.md` (the full mechanical ground truth; the Definition-of-Ready, batch-approval, final-ratification (T19), and merge-approval (T20) gates live here).

## Fractal / altitude

The same five words recur at every altitude and are **altitude-labeled** so they scale up the crosswalk:

- **Default altitude = the Scope** (ticket-sized — the right grain for most real, brownfield work picked up from a GitHub issue or a Jira ticket). CE's atom is already Scope-sized.
- **Higher altitudes** (epic, project) reuse the same words via the optional crosswalk (PRD → epic → story → task): e.g. *project-Frame*, *epic-Shape*.
- **Collapse at small grain.** For a small Scope, `Frame` folds into `Shape` (and Solutioning is part of `Shape`); the phases split out only as the grain grows. This is what makes the vocabulary **fractal** rather than a fixed project-level pipeline.
- **`Ship` is plural by design.** The terminal-outcome axis has five values, so `Ship` covers a merged PR **and** `research_delivered` **and** a ratified `no_change` — not only `pr_merged`.

## BMAD correspondence (recognizability)

CE implements BMAD's four-phase workflow in its own externally-graded way — each phase output is a *ratifiable artifact*, not just a document:

- `Frame ≈ Analysis`
- `Shape ≈ Planning + Solutioning`
- `Build ≈ Implementation`
- **`Review` / `Ship` = CE's first-class governed tail.** BMAD folds review and ship into Implementation; **CE separates them because external grading plus the governed merge is the differentiator** — the grader lives outside the agent, and "done" is a ratified, merged artifact, not the agent's say-so.

## Non-goals

- **Not** a change to the mechanical state machine — every enum above is conserved verbatim.
- **Not** a v1 change (v1.0 is frozen).
- **No** CI terminology guard in this canon — docs-canon is manual hygiene (the existing terminology guard is scoped to `specs/v2/`, never `docs/`); a docs-scoped guard is a separately-grounded follow-on.

## Provenance & companions

GH issue #159 (2026-06-07); the v3.1 coordination-layer design thread. Pairs with [`pilot-uiux-model.md`](./pilot-uiux-model.md) (where the vocabulary surfaces) and [`pilot-roadmap.md`](./pilot-roadmap.md) (the G-6 coordination layer and the G-7 product surface consume it). The mechanical ground truth is [`agentic-sdlc-operating-model.md`](./agentic-sdlc-operating-model.md).

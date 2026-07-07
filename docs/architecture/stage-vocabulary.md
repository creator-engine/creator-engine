# CE v3 — Vocabulary (canon)

*Canon decision + dual-mapping reference for CE's user-facing vocabulary (provenance: 2026-06-07/08 design sessions; GH #159). **CANON — terminology-canon-tracked.** CE presents users **clear words** (the skin) over **conserved mechanical names** (the engine); this document is the authority for both and their correspondence. It covers three user-facing surfaces — the **stage phases** (`Frame → Shape → Build → Review → Ship`), the **Scope-card / gate fields**, and the **◆ CE Completion Report**. Execution status lives in the project README's **Current Status** section.*

## The decision

CE presents users a clear, intuitive, **fractal** cognitive-phase vocabulary for "what am I doing right now," while **conserving the existing mechanical state machine underneath**. The vocabulary is CE canon — a peer to **Operator** and **Controller** — and surfaces in the `ce session` status line, the ◆ CE Completion Report, the board, and these docs.

**The canon lexicon (locked 2026-06-07):**

> **Frame → Shape → Build → Review → Ship**

- **Frame** — understand and bound the problem/ticket: what is being asked, why, and what "done" means.
- **Shape** — turn the framed problem into a ratifiable Scope: Goal, Done-when, Change-type, and the plan. Ends when the Scope is ratified and Ready for Build.
- **Build** — execute the ratified Scope in one governed, boxed run.
- **Review** — grade the result against the acceptance criteria (external grading; evidence, not transcripts).
- **Ship** — the governed terminal delivery: a merged PR, delivered research, or a ratified no-change.

### Conserve the machine (load-bearing principle)

The cognitive vocabulary is a **skin**. The precise mechanical state machine remains the **engine / board / evidence** layer where governance lives, and is **conserved verbatim** — this canon renames or removes **zero** enums. The skin sits over the machine and maps to it; it never replaces or hides it. A curious user can always "dig in" to the machine under the skin (see [The conserved machine](#the-conserved-machine-dig-in-layer)).

## The dual mapping (the core artifact)

User-facing cognitive phase ↔ board/pipeline label ↔ mechanical spec-lifecycle state ↔ gate ↔ BMAD phase:

| Cognitive phase | Board label | Spec-lifecycle state | Gate | BMAD phase |
| --- | --- | --- | --- | --- |
| **Frame** | `BACKLOG` | `draft` | — | Analysis |
| **Shape** | `SHAPE → READY` | `draft → ready` | **front gate:** Definition-of-Ready (scope + `acceptance_criteria` + verification) **+** Scope ratification | Planning + Solutioning |
| **Build** | `RUN` | `in_progress` | *(container lifecycle: `provision → run → collect → teardown`)* | Implementation |
| **Review** | `REVIEW` | `verified` | external grading (review-evidence; **non-ratifying**) | — *(CE first-class tail)* |
| **Ship** | `MERGE` | `ratified → done` | **back gate:** final ratification (mutation_class-tiered) **+** governed merge | — *(CE first-class tail)* |

Notes:

- **`Shape` is deliberately overloaded.** It is both a cognitive phase and (as `SHAPE`) one of the board states it subsumes. The user-facing `Shape` spans board `SHAPE → READY` plus the DoR gate: the dominant phase keeps its name.
- **The two-end gate chain is where governance binds.** The **front gate** (Shape→Build) is the Definition-of-Ready plus Scope ratification; the **back gate** (at Ship) is the `mutation_class`-tiered ratification plus the branch-protection-enforced merge. `Build` and `Review` are the middle.

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

## The Scope-card / gate-field vocabulary (2nd vocabulary — locked 2026-06-08)

The same skin-over-conserved-machine principle applies to the **fields of a Scope** (and the Definition-of-Ready gate it must pass). The user-facing labels are clear; the **schema field-names are conserved verbatim** (the engine/governance layer — `schemas/scope.schema.yaml`, shipped at G-6, is unchanged by this canon):

| User-facing label (skin) | Conserved schema field (engine) | Why clearer |
| --- | --- | --- |
| **Goal** | `intent` | plain — "what I'm trying to do" |
| **Done when** | `acceptance_criteria` | names it as the *testable done-oracle* (the external grader's target), not an Agile artifact |
| **Budget** | `appetite` | optional lane-aware cap detail; it also becomes the run's spend cap via the G-5 join |
| **Change type** | `mutation_class` | "what kind of change, and how risky" — the risk tier (`docs < code < schema < deploy < …`) that drives the back gate |
| **Ready** | `definition_of_ready` | maps straight onto the board `READY` state — the word already exists in the machine |

So a Scope card reads, e.g.: `◆ CE · Shape → "rate-limit /api/login"  (Done-when 3 · Budget S · Change-type code · Ready ✓)`.

- **The atom-word `Scope` is kept** — distinctive, brandable, and load-bearing across the coordination hierarchy and the G-6 Scope object. It is not relabeled.
- **Conserve the fields.** As with the stage phases, the labels are a presentation skin; `schemas/scope.schema.yaml`'s `intent / acceptance_criteria / appetite / mutation_class` and the `definition_of_ready` predicate are unchanged. The shaping dialogue that *fills* these fields is designed in [`shaping-ux.md`](./shaping-ux.md); the plain-language walk-through is in [`../guide/understanding-ce.md`](../guide/understanding-ce.md).

## The ◆ CE Completion Report vocabulary (3rd vocabulary — locked 2026-06-08)

The per-run **◆ CE Completion Report** answers three plain questions — *what happened · did it pass · what's next* — over the conserved evidence chain. Same skin-over-conserved-machine principle:

| User-facing label (skin) | Conserved source (engine) | Note |
| --- | --- | --- |
| **Outcome** | the `outcome` enum (`schemas/runtime-evidence.schema.yaml:247`) | label kept; **render the values plainly:** `pr_opened`→"PR opened", `pr_merged`→"Merged", `review_submitted`→"Review submitted", `research_delivered`→"Research delivered", `no_change`→"No change needed" |
| **Verdict** | the grading synthesis (Done-when met · CI · spend · in-scope) | **was "determination"** — the one real relabel; it *is* the grade, and "Verdict" reinforces that the grader lives outside the agent |
| **Next** | derived (Outcome × stage × Change-type) | was "next step" |
| **Artifacts** / **Inspect** | the artifact enumeration + the `ce`-style inspect commands | kept — already plain |

The report inherits the **other two vocabularies** for consistency: `AC`→**Done-when**, `class`→**Change-type**, `spend of S`→`of `**Budget**, and `manifest-fidelity`→**"in scope ✓"** (plain for "the diff stayed inside the closed manifest"). So a report reads:

```
Outcome   PR opened → #7
Verdict   Done-when 3/3 met · tests green · in scope ✓ · 14% of Budget S
Next      → Review PR #7  (Change-type code → your approval)
```

- **Conserve the machine.** The `outcome` enum and the underlying grading signals (acceptance-criteria pass, CI status, spend, manifest-fidelity) are unchanged; only the user-facing labels are added. The cockpit ([`cockpit.md`](./cockpit.md)) re-renders the same report at fleet scale.

## Non-goals

- **Not** a change to the mechanical state machine — every enum above is conserved verbatim.
- **Not** a change to the Scope schema or the G-6 contract — the field-names (`intent` / `acceptance_criteria` / `appetite` / `mutation_class`) and the `definition_of_ready` predicate are conserved; only the user-facing labels are added.
- **Not** a change to the run-outcome model — the `outcome` enum (`runtime-evidence.schema.yaml:247`) and the grading signals are conserved; the Completion-Report labels are presentation only.
- **Not** a v1 change (v1.0 is frozen).
- **No** CI terminology guard in this canon — docs-canon is manual hygiene (the existing terminology guard is scoped to `specs/v2/`, never `docs/`); a docs-scoped guard is a separately-grounded follow-on.

## Provenance & companions

GH issue #159 (2026-06-07, the stage phases); the 2nd vocabulary (Scope-card fields) and the 3rd vocabulary (◆ Completion Report) both locked 2026-06-08 — all in the v3.1 coordination-layer design thread. Pairs with [`shaping-ux.md`](./shaping-ux.md) (the shaping dialogue that fills the Scope), [`pilot-uiux-model.md`](./pilot-uiux-model.md) (where the vocabulary surfaces), [`cockpit.md`](./cockpit.md) (the post-pilot graduation that re-renders the same vocabulary at fleet scale), and the user guide [`../guide/understanding-ce.md`](../guide/understanding-ce.md) (the plain-language walk-through). The G-6 coordination layer and the G-7 product surface consume this canon. The mechanical ground truth is [`agentic-sdlc-operating-model.md`](./agentic-sdlc-operating-model.md).

---
kind: decision-record
record_type: adr
schema_version: "1"
id: ADR-0009
title: "Bounded work-units (small batches) as a core CE tenet"
status: accepted
date: 2026-06-21
decision_makers: ["ce-arch-tenets"]
consulted: []
informed: []
review_by: 2026-12-21
mutation_class: governance
ratification:
  ratified_by: ce-dev-2
  ratified_at: "2026-06-21"
  ratification_prompt_sha: "6567380f5395d586f70907749e2a62f44fffacaf2df70affe044d9abc5923983"
  quorum: n1_solo
  # N=1 native mode: this privileged, accepted governance record was ratified by
  # the sole resolved human (the Operator, login ce-dev-2 per .ce/coordination.yml
  # identity_map → human_id peer-operator), with a distinct agent author
  # (ce-arch-tenets) — honest solo quorum. The anchor is the sha256 of the
  # Operator-ratified ratification prompt for graduating the bounded-work-units
  # tenet (ce-ops#165).
evidence_refs:
  - kind: issue
    ref: "ce-ops#165 — tracking issue: graduate the bounded-work-units / small-batches tenet to an ADR; the parent of #163 and #164."
    tag: tracking-issue
  - kind: issue
    ref: "ce-ops#164 — controlled merge system (merge queue / train) bounding the MERGE-UNIT; the ~200/400-line grounding research lives here."
    tag: merge-unit
  - kind: issue
    ref: "ce-ops#163 — foreman delegation bounding the TASK-UNIT (action-type × irreversibility, not lines)."
    tag: task-unit
  - kind: doc
    ref: "DORA / Accelerate — 'work in small batches' as a value-stream capability correlated with throughput and stability; the shared root principle this ADR names."
    tag: dora-small-batches
  - kind: doc
    ref: "ce-energy-efficiency-ceo-mode-gravity — delegation gravity; bounded units are what makes deep delegation tractable rather than runaway."
    tag: ceo-mode-gravity
  - kind: doc
    ref: "ce-no-mvp-quality-from-day-1 — prevent-by-design over observe-and-react; a bounded unit prevents the failure mode instead of cleaning it up."
    tag: no-mvp
  - kind: doc
    ref: "ce-product-north-star / grader-outside-the-agent — a bounded unit is the natural quantum the grader-outside gates at each seam."
    tag: grader-outside
---

# Bounded work-units (small batches) as a core CE tenet

## Context and Problem Statement

CE has been treating two structural problems as separate engineering tasks:
**"endless rebase-hell"** (large, long-lived branches drift from `main`, collide
on merge, and force repeated rebases) and the **"endless seats bottleneck"** (a
worker handed an unbounded task runs long, accumulates irreversibility, and
becomes the throughput choke). They look unrelated — one is a VCS/merge problem,
the other a delegation/scheduling problem — so they have attracted separate,
local fixes.

They are not separate. Both are the same value-stream failure: **the unit of work
is unbounded.** The DORA / Accelerate research names the corresponding capability
plainly — *work in small batches* — and shows it as a root driver of both
throughput and stability (`dora-small-batches`). When the batch is small, drift
is small, blast radius is small, and the grader-outside has a tractable quantum to
gate. When the batch is unbounded, drift compounds (rebase-hell) and delegation
cannot complete or be safely ratified (the seats bottleneck). Naming the shared
root *once* — as a tenet — is what lets the two downstream fixes (#163, #164) be
recognized as two expressions of one principle rather than two coincidences. This
ADR graduates that tenet (ce-ops#165) from a working principle to a ratified
Decision Record.

## Decision Drivers

- **One root, two symptoms.** Rebase-hell and the seats bottleneck share a single
  cause (the unbounded work-unit); a tenet is the right altitude to fix the cause
  rather than the two symptoms (`tracking-issue`, `dora-small-batches`).
- **Prevent-by-design, not observe-and-react** (`no-mvp`): a bounded unit prevents
  the failure mode at creation time instead of detecting and cleaning it up later.
- **Delegation gravity** (`ceo-mode-gravity`): CE's usage attractor is deep
  delegation; deep delegation is only tractable when each delegated unit is
  bounded and individually ratifiable.
- **Grader-outside-the-agent** (`grader-outside`): a bounded unit is the natural
  quantum the external grader gates at each seam — small enough to judge cleanly.
- **Same principle, different seam.** The bound must be expressed per seam with the
  *metric that fits that seam*; a single global metric (e.g. "lines everywhere")
  would be wrong for the delegation seam.

## Considered Options

1. **Keep fixing the two problems independently** — a merge-queue patch here, a
   delegation heuristic there. Rejected: it treats symptoms, duplicates rationale,
   and lets the two fixes drift out of conceptual alignment.
2. **One global bound (e.g. a single line-count cap everywhere)** — rejected: a
   line cap is meaningful for a merge-unit but meaningless for a task-unit, where
   the real bound is action-type and irreversibility, not size on disk.
3. **Adopt "bounded work-units / small batches" as a core tenet (chosen)** — name
   the shared root once, then let it manifest per seam with a seam-appropriate
   unit and metric. The two existing tickets (#163, #164) become children of this
   tenet, not independent efforts.

## Decision Outcome

Adopt **bounded work-units (small batches) as a core CE tenet.** The unit of work
at every CE seam is deliberately bounded; the *reason* is constant (efficiency +
prevent-by-design + a tractable quantum for the grader-outside), while the
**unit and its metric vary per seam**:

1. **The MERGE-UNIT — bounded by a controlled merge system** (`merge-unit`,
   ce-ops#164). A merge queue / merge-train sits between every dev and `main` and
   bounds how much can land at once. The fitting metric here is **size**, grounded
   by the #164 research at roughly **~200 lines (target) / ~400 lines (ceiling)**
   per merge-unit. Small merge-units keep drift small and collisions rare — this
   is what kills *rebase-hell* at its root rather than absorbing it with more
   rebasing.

2. **The TASK-UNIT — bounded by foreman delegation** (`task-unit`, ce-ops#163). A
   foreman bounds what a single delegated worker is handed. The fitting metric
   here is **NOT lines** — it is **action-type × irreversibility** (the same
   consequence × novelty × irreversibility axis CE already uses for the authority
   bar). A task-unit is bounded so a worker completes, is individually
   inspectable, and is individually ratifiable — this is what relieves the *seats
   bottleneck* at its root rather than scheduling around it.

Both manifestations are the **same tenet**: bound the unit, at the seam, with the
metric that fits the seam. New seams that appear later inherit the tenet and must
declare their own unit + metric; they do **not** inherit a specific number (200/400
is the merge-unit's metric, not the tenet's).

## Relationships

- **Parent of ce-ops#163 (task-unit / foreman delegation)** and **ce-ops#164
  (merge-unit / controlled merge system).** Both are downstream expressions of
  this tenet; ce-ops#165 is the tracking issue for this graduation.
- **Connects to `ce-energy-efficiency-ceo-mode-gravity`** — bounded units are the
  precondition that makes deep delegation (the CEO-mode attractor) tractable.
- **Connects to `ce-no-mvp-quality-from-day-1`** — the tenet is a prevent-by-design
  guard, the opposite of "good enough, clean it up later."
- **Connects to `ce-product-north-star` / grader-outside-the-agent** — the bounded
  unit is the quantum the external grader gates at each seam.

## Consequences

- **Good — kills both structural problems at one root.** Rebase-hell and the seats
  bottleneck are addressed by *one* named principle, so the two fixes (#163, #164)
  stop being coincidental and start being coherent expressions of a tenet.
- **Good — prevent-by-design.** The bound applies at unit-creation time; the
  failure mode (unbounded drift / unbounded delegation) is prevented, not detected
  and remediated.
- **Good — scales by delegation depth.** Because each seam bounds its own unit,
  the tenet composes: deeper delegation chains stay tractable because every link
  is itself bounded and individually ratifiable.
- **Good — one rationale, audited once.** A single ratified tenet means future
  seams reuse the reasoning instead of re-litigating "why small?" each time.
- **Cost / risk — bound-setting is now an explicit obligation.** Every seam must
  declare and defend its unit + metric; an unbounded seam is now a tenet
  violation, not an oversight. (Acceptable: that explicitness is the point.)
- **Risk — the metric can be mis-ported across seams.** The 200/400 line numbers
  are the merge-unit's metric and must **not** be applied to the task-unit (whose
  metric is action-type × irreversibility). Guard: each seam's metric is recorded
  with its own ticket (#163 vs #164), never globalized.
- **Risk — over-fragmentation.** Bounds set too tight could fragment work into
  coordination overhead. Mitigation: the metric per seam is tuned with evidence
  (the #164 research grounds the merge-unit numbers), not set by fiat, and is
  revisited at `review_by`.

# BRIEF — dev-4 — 2026-07-07 ~20:5xZ — U1 REVISED: Option A DESIGN DOC (not implementation)

Your BLOCKED-DESIGN was the correct act — the questions you raised are governance
semantics that must be designed and reviewed before code. Same unit, repurposed
design-first. COMMIT-ONLY; signal `READY <branch> <sha> <evidence-path>` when done.
Keep branch `ce-491-optiona-merge-intent` (worktree you already have, clean at
bd5b1f83 — reuse it).

## U1r — design doc `docs/design/ce-491-optiona-merge-intent.md` (work class: S)

GOAL: a review-ready design for Option A (merge-time intent materialization) that
answers, concretely and fail-closed, the exact questions you raised:

1. OWNING ACTOR: evaluate the three candidates — (a) the merge-gate queue daemon
   (observes merges already; would gain a NARROW direct-commit-to-main authority for
   materialization commits only), (b) the integrator (merge-mechanics owner), (c) a
   merge-group CI job. Recommend ONE with an honest trade-off table. Constraint: the
   merge commit itself is authored by the forge's merge queue, so materialization is
   necessarily a post-merge step by whichever actor. Constraint: the merge gate is a
   policy singleton; do not design a second gate-authority holder.
2. AUTHORITY CONTRACT: whatever actor you recommend, spell out the new authority it
   needs (e.g., push a materialization commit to main), its exact bounds (only
   .ce/brain/assertions.yaml + consumed intent files, nothing else), and state
   explicitly that ARMING this authority is an Operator decision — design it, don't
   grant it.
3. INTENT LIFECYCLE: `.ce/brain/append-intents/<branch-slug>.yaml` (or your
   better-argued location) — schema sketch, consume-and-remove vs retain-as-evidence
   semantics at materialization, and what the landed tree must look like after
   closeout (zero unconsumed intents from merged PRs = an invariant a validator can
   check).
4. FAILURE/CRASH MODEL: materialization actor dies mid-act — idempotent resume rules;
   unprovable live tail at materialization time — fail-closed hold + surfaced state
   (align with the #882 gate's vocabulary); a malformed intent that passed PR CI but
   fails at materialization — quarantine path, never silent drop.
5. EVIDENCE CONTRACT: where mediation evidence lives (ledger record fields, PR
   comment, daemon log), deterministic and auditable.
6. INTERACTION with the #882 stale-tail gate: intent-carrying PRs no longer touch
   assertions.yaml directly, so the gate's serialize-behind-zero-drift pressure
   disappears for them; state how legacy pre-chained deltas remain gated unchanged.
7. Scheduled drill + test plan for the whole loop.

SCOPE: the design doc + `.ce/changelog/ce-491-optiona-merge-intent.md` + carrier
`.ce/pr-manifests/ce-491-optiona-merge-intent.md` (slug==branch, self-inclusive,
`- **Declared work class:** S`). Public-docs lens: no internal hostnames/seat names;
generic placeholders only.

Standing preflight directive (ce-ops#303): FULL local preflight before
commit-for-harvest.

STOP LINE: design only — no implementation code, no schema files outside the doc's
inline sketches, no pushes, no gate acts. If a question above cannot be answered
without an Operator ruling, write the options + recommendation into an "Open Operator
Questions" section and mark it BLOCKING-FOR-IMPLEMENTATION rather than stopping.

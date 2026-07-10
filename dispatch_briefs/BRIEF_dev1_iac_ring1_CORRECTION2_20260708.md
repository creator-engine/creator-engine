# CORRECTION 2 — dev-1 — 2026-07-08 — unblock U2 ce-ring1-launch-provenance

Your U2 block was correct discipline: `.ce/state/decisions/DECISIONS_20260708.md` is the
controller's LOCAL state ledger (dual-written controller-side), not a tracked file on
origin/main — my brief wrongly implied you could verify it from the repo. The authoritative
decision text is embedded below, verbatim from the controller ledger. This embedded copy IS
your provenance source; treat this brief (hash-pinned at dispatch) as the ratification anchor.

## Embedded Operator decisions (verbatim, DECISIONS_20260708.md, controller ledger)

> 3. C5 PROMOTION DECLARED: containerized merge-gate daemon (ce-queue-daemon) is THE
>    gate; host daemon demoted to ROLLBACK-ONLY (no warm-standby). Evidence:
>    C5_PARITY_ASSESSMENT_20260707.md + final addendum.
>
> 4. RING-1 PRE-ACTS AUTHORIZED: (a) launch-wired provenance update in harness_matrix.py
>    (Operator-authorized, controller-driven); (b) live governed `ce launch --harness
>    codex` Ring-1 smoke writing the evidence packet. FLIP still returns to Operator
>    with the real packet.

## Adjusted U2 instructions

- Provenance string in `harness_matrix.py`: cite the decisions by name and date, not by a
  repo path — e.g. `"Operator-authorized pre-act (decision 4, Operator decisions
  2026-07-08); containment accepted per C5 promotion (decision 3, same ledger); promotion
  evidence packet still pending = ticket 480"`. Keep the ticket 480 reference. Do NOT
  reference a repo file path for the ledger.
- PR body: include the line `Operator-authorized: decision 4, Operator decision ledger
  2026-07-08 (controller state root, dual-written); decision text embedded in dispatch
  brief BRIEF_dev1_iac_ring1_CORRECTION2_20260708.md (sha-pinned at dispatch).`
- Everything else in the original U2 spec unchanged: the single `_yellow(...)` →
  `_green(...)` cell change in `_codex_rows`, the single YELLOW→GREEN test assertion,
  regenerate HARNESS_SUPPORT_CAPABILITY_MATRIX.md via the existing renderer, changelog +
  carrier (slug ce-ring1-launch-provenance), work class tiny, full `ce validate-pr`
  green → push → PR → `READY ce-ring1-launch-provenance <sha> PR#<n>`.
- Stop line unchanged.

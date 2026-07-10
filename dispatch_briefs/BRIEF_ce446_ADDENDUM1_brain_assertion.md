# ADDENDUM 1 — ce-446-base-resolve-robust — BLOCKED resolved: brain-assertion update authorized

Your BLOCKED signal was correct stop-line discipline. Controller verification: the tracked ledger
`.ce/brain/assertions.yaml` on main carries hash-pinned assertions with
`evidence_ref: .github/workflows/validate.yml` (e.g. `brain-assertion-validate-workflow-drift-gate`,
scoped to that artifact with a content_hash). Editing validate.yml therefore legitimately obligates
a ledger update in the same PR — this is the drift gate working as designed, not a false-RED.

## Authorization (closed-set extension)
`.ce/brain/assertions.yaml` is ADDED to your allowed paths for this unit. Everything else in the
original brief stands unchanged.

## How to update (chain-safe — do NOT hand-edit hashes)
1. Use the brain tooling, not manual edits: `ce brain correct` (appends a supersession marker plus
   the corrected assertion; preserves the prev_hash chain). Consult `ce brain --help` /
   `ce brain verify` for exact flags; the corrected assertion should re-pin the NEW content hash of
   your edited validate.yml for each assertion whose scope/evidence_ref names that artifact.
2. Do NOT restructure, re-order, or rewrite existing ledger entries; supersession-append only.
   Do NOT convert the pin to a probe/projection form — that migration belongs to a separate
   program, not this PR; minimal correct move = supersede with the updated content_hash.
3. Run `ce brain verify` green, then re-run the FULL `ce validate-pr` — one pass GREEN.
4. Regenerate the carrier (carrier_gen API, same base) so it includes `.ce/brain/assertions.yaml`;
   amend or add to your commit; self-push and open the PR per the original brief (including the
   `Closes creator-engine/ce-ops#446` line and the work-class line).

## Unchanged
Stop line, signed-artifact rule, and all other constraints from
/var/tmp/BRIEF_ce446_base_resolve_robust.md remain in force.

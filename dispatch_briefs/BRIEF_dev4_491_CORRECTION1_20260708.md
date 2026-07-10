# CORRECTION 1 — dev-4 — ce-491-optiona-slice1 — resolve brief↔design conflict (controller ruling)

Your BLOCKED was correct: the brief's error mapping contradicted the design, and the design
wins. Controller ruling — follow the design's failure-state machine VERBATIM:

1. A malformed / validation-failing intent discovered at materialization time (post-CI,
   i.e. any `BrainAppendRefusal` raised by `IntentDiscovery` in `Materializer.run_dry`)
   enters **HELD** with reason `brain_intent_materialization_failed`:
   - write the `QuarantineWriter` artifact (out-of-band, `.ce/state/brain-intent-quarantine/`),
   - write the `HeldStateStore` record with that reason,
   - emit a `held` event to the JSONL log,
   - release the lease,
   - return `DryRunOutput` with `status="held"` and the refusal detail carried in
     `refusal_reason`.
2. The brief's separate `"refused"` outcome class: keep it in the `DryRunOutput.status`
   enum ONLY if the design itself defines a distinct refusal outcome at materialization
   time; if it does not, drop `"refused"` from the enum entirely and update the dataclass
   docstring to name the two outcomes (`would_materialize` | `held`). Derive this from the
   design text, not from the original brief.
3. Adjust the affected tests accordingly (`test_brain_intent_materializer_dryrun.py` and
   `test_brain_intent_materializer_hold.py`): malformed intent → `status="held"` +
   quarantine artifact + held record with `brain_intent_materialization_failed`; there is
   no test asserting a `"refused"` status unless justified by point 2.

Everything else in BRIEF_dev4_491_optiona_slice1_20260708.md stands unchanged, including
all HARD INVARIANTS, the authorized path set, and the stop line. Same branch, same
worktree (/var/tmp/ce-491-optiona-slice1 — it exists and is clean at origin/main; proceed
there). Signals unchanged: `READY ce-491-optiona-slice1 <commit-sha>
.ce/pr-manifests/ce-491-optiona-slice1.md` / `BLOCKED ce-491-optiona-slice1 <reason>`.

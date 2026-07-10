# BRIEF — dev-4 — 2026-07-08 ~00:xxZ — 1 unit: PR #889 design revision (your Option A design)

Your Option A design was harvested as PR #889 and received REQUEST-CHANGES (head
4cbc4c660). Revise on the SAME branch `ce-491-optiona-merge-intent`. COMMIT-ONLY:
signal `READY <branch> <sha> <evidence-path>`; controller harvests and updates the PR.
Worktree: fresh /var/tmp checkout; `git fetch origin ce-491-optiona-merge-intent` and
base on 4cbc4c660 (it contains a harvest carrier fixup). Commit early and often;
PYTEST_ADDOPTS="-n 2" for any test runs. DESIGN-ONLY stays in force.

## Findings to resolve (full text in the PR #889 review; substance embedded)

B1 (BLOCKER): your sketch ignores the EXISTING tracked schema
`validators/creator_engine_validator/brain_append_intent.schema.yaml` and worker
`brain_append_worker.py` — which YOUR OWN ce-488 unit just expanded (your local
worktree /var/tmp/ce-488-memory-layer-slice1 has the latest head; read the schema
from there or from the origin branch ce-488-memory-layer-slice1). Add an explicit
reconciliation section: state whether Option A's PR-carried intent envelope
SUPERSEDES, EXTENDS, or COEXISTS-AT-A-DIFFERENT-PIPELINE-STAGE with the tracked
schema; reconcile field-by-field (kind discriminator, schema_version string form,
intent_kind routing, payload shape, PR-binding fields). The design must name the
tracked file and worker; delete the false "not a tracked schema file" sentence.

M1: specify the FULL materialization ledger-record schema (not just the mediation
block): field list, canonical ordering, and an explicit prohibition on
execution-time-variable fields in the record body — make byte-identical idempotency
verifiable.
M2: name WHERE materialization_key persists (recommend: a deterministic trailer line
in the materialization commit message AND a field in the appended record) so
crash-after-push detection is implementable identically by any instance.
M3: specify HELD-state cascade: whether HELD blocks other pending intents (recommend:
per-component hold, others proceed), validator treatment of a HELD intent from a
merged PR (not a hard failure until closeout window expires — define the window),
and HELD re-entry on daemon restart.
M4: name the validator gate for the intent-XOR-direct-edit rule and REFUSE the hybrid
PR (intent file + direct assertions.yaml edit) explicitly as a hard gate.
M5: specify the lease: storage location, expiry, and exclusion scope — and reconcile
with M6.
M6: add the FOURTH Open Operator Question, BLOCKING-FOR-IMPLEMENTATION: materializer
topology — strict singleton vs multi-instance-under-external-lock; note a second
instance = an additional writer to main, bearing directly on Question 1.

Minors (same revision): m1 invariant "can"→"must"; m2 name the merge-order discovery
mechanism; m3 specify HELD recovery paths (follow-up-PR semantics + how manual
recovery is authorized pre-arming); n1 covered by B1; n2 specify dry-run/advisory
output format + destination; n3 state the gate-daemon singleton assumption explicitly.

EVIDENCE: changelog fragment extended with a revision line; carrier unchanged unless
paths change; evidence summary naming each finding's resolution section.
Standing preflight directive (ce-ops#303): FULL local preflight before
commit-for-harvest (-n 2 cap; ENV-SKIP fallback with everything else green).

STOP LINE: design doc + changelog + carrier only; no schema/code files; no pushes,
PRs, gate acts, signing. If reconciliation with the tracked schema forces a decision
that is Operator-level, add it to Open Operator Questions rather than deciding it.

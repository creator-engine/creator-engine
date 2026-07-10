# Seed Brief: ce-388-payload-data-only — brain-assertion supersede (round 4)

- Context: PR #740 (branch ce-388-payload-data-only, your round-3 head 9eb5f2b7) is DRAFTED after failing its merge group on brain drift: assertions d1b-10/-11/-12 pin evidence_sha256 of `validators/creator_engine_validator/forge/integrator_belt.py`, which this branch modifies. Same class you fixed for ce-402 — same remedy, and main now has everything you need (#743 chain-walk + #742's precedent supersedes).
- Branch: `ce-388-payload-data-only` (EXISTING — your /var/tmp/ce-388-payload-data-only worktree). Role: implementer.

## Steps
1. Fetch origin; merge origin/main into the branch (brings #742/#743/#744; ledger now has 73 active records incl. three -v3s from ce-402).
2. Via the documented `correct_claim` path, append -v3 supersedes for:
   - `brain-assertion-d1b-10-merge-queue-conflict-gate-v2`
   - `brain-assertion-d1b-11-approval-green-triggers-queue-v2`
   - `brain-assertion-d1b-12-approval-current-head-required-v2`
   re-pinning evidence_sha256 to THIS BRANCH's `forge/integrator_belt.py` (recompute the sha; never hand-transcribe).
3. SEMANTIC CHECK (report explicitly per assertion): each claim's statement must still be TRUE of the branch's integrator_belt.py (merge-queue conflict gating; approval+green triggers enqueue; approval must be on current head). Your branch's payload-schema changes should not falsify them — if one IS false, STOP and report; no hash-papering.
4. Update the hard-coded active-count in `validators/tests/unit/test_ce_brain_drift.py`: 73 → 76 (and any sibling totals, minimally).
5. Update `.ce/changelog/ce-388-payload-data-only.md` (one line) and regen the carrier via carrier_gen API (path set grows by assertions.yaml + the drift test).
6. Full preflight GREEN one pass (`ce validate-pr`, CI-parity; ssh-keygen known-exception rule applies), commit, then emit exactly:
   `READY-FOR-HARVEST ce-388-payload-data-only <full-sha>`

## Allowed paths
`.ce/brain/assertions.yaml` (append-only) · `validators/tests/unit/test_ce_brain_drift.py` (count bump only) · `.ce/changelog/ce-388-payload-data-only.md` · `.ce/pr-manifests/ce-388-payload-data-only.md` · main-merge conflict resolution (report any).
Do NOT touch conveyor_daemon.py, integrator_belt.py, or any other code beyond mechanical merge resolution.

## Stop line
No pushes, no PR actions, no approvals, no merges, no gate/wall/daemon config changes, no toolchain self-update. If correct_claim refuses or the ledger state surprises you, STOP and report.

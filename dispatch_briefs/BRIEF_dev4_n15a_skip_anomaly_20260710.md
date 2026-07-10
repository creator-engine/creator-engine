# DISPATCH — dev-4 — 2026-07-10 — unit: gate skip-anomaly alarm + approved-PR-age SLO — class S
Role: implementer foreman. Signal: `SELF-PUSHED ce-n15a-skip-anomaly <sha> PR=<number>`
or `READY-FOR-HARVEST ce-n15a-skip-anomaly <sha>` (fallback — see Signal section below)
or `BLOCKED ce-n15a-skip-anomaly <one-line-reason>`.
Branch `ce-n15a-skip-anomaly` off freshly fetched origin/main OR LATER. Worktree
/var/tmp/wt-ce-n15a-skip-anomaly. Standing preflight directive: run
`ce validate-pr --profile contained-seat` if your environment can; else focused tests +
BLOCKED(env) per protocol. PRE-SIGNAL CHECKLIST: focused tests green + confidentiality check:
`python -m pytest validators/tests/unit/test_public_docs_confidentiality.py::test_tracked_text_files_contain_no_new_confidential_or_internal_references -q`

## Context (embedded)

The merge-queue daemon's integrator belt emits per-pass decision records (skip/defer/enqueue with
a reason string) and completed-pass events. A recent incident observed every open PR skipped with
an IDENTICAL reason string for 100+ consecutive passes with zero alarms — the silence was
indistinguishable from progress until hours later when manual inspection caught the pattern. This
unit is DETECTION-ONLY: record skip anomalies and approve-age violations in structured event logs,
trigger loud alarms via journald, and make the conditions observable. No mutation authority, no
automatic PR closure, no daemon steering — logs and records only.

## Unit

In the queue-daemon pass loop (`validators/creator_engine_validator/forge/integrator_belt.py` —
same territory as the recent liveness-state export; read that pattern first):

1. **Skip-reason recurrence tracker:** at the top of each pass, track per-pass skip reasons
   alongside the PR set being evaluated. If the (reason, PR-set-signature) tuple recurs
   identically for >= K consecutive passes (K env-tunable via `CE_SKIP_ANOMALY_K`, default 3),
   emit a structured alarm event record (JSONL, same durable-event idiom as the liveness-state
   file) with class `skip_anomaly_recurrence` and a journald line flagged `PRIORITY=3` (ERR).
   The alarm record must name the reason, the K value, and the pass count. On the first change
   to a different reason (or change to the PR set), reset the counter.

2. **Oldest-approved-PR-age SLO:** across the pass loop, track the oldest PR observed in
   `approved_unmerged` state at the start of each pass. If that PR has remained approved-but-
   unmerged for > N consecutive passes (N env-tunable via `CE_APPROVED_AGE_N`, default 10),
   emit a distinct alarm record with class `approved_pr_age_exceeded`, naming the PR number,
   its approval age in passes, and the N threshold. Emit once per distinct PR; reset the
   counter when that PR merges or loses approval.

3. **Record format:** both alarms use the same durable-event JSONL path as existing liveness
   exports (consult `integrator_belt.py` for the precedent). Each record includes: `timestamp`
   (ISO 8601), `pass_number`, `alarm_class` (one of `skip_anomaly_recurrence` or
   `approved_pr_age_exceeded`), `details` (dict with reason/pr_count/age/threshold as
   applicable), `journald_priority` (for the loud flag).

4. **Tests:** must verify that skip-reason recurrence triggers exactly at K, resets on change,
   oldest-approved-age triggers at > N, resets on merge, and alarm records are well-formed. All
   existing belt tests must remain green and untouched.

## Files (allowed writes)

- `validators/creator_engine_validator/forge/integrator_belt.py` — skip-reason recurrence +
  approved-age tracking + alarm emission
- `validators/tests/unit/test_integrator_belt.py` (or the existing belt test module) — four
  focused tests for recurrence trigger/reset, age trigger/reset, record format, existing tests
  green
- `.ce/changelog/ce-n15a-skip-anomaly.md` — changelog fragment
- `.ce/pr-manifests/ce-n15a-skip-anomaly.md` — carrier (slug=branch) with exactly
  `- **Declared work class:** S`

Product lens throughout. Synthetic environment defaults. No internal ticket references in
committed content.

## Stop lines

Every other gh mutation path, `tools/egress-broker/**`, `daemon_lease.py`, all `deploy/**`,
`ce_cli.py`, `v3_cli.py`, `secret_identity.py`, `.ce/brain/assertions.yaml`, brain ledger,
every in-flight module.

## Signal

After focused tests pass and the confidentiality check is green:

1. Commit all changes on branch `ce-n15a-skip-anomaly`.
2. Push through the broker socket by running, inside the container:
   ```
   python3 /var/tmp/canary.py --repo /workspace/creator-engine --branch ce-n15a-skip-anomaly
   ```
   The canary client is the push client: it pushes the branch and opens the PR via the live
   broker socket.
3. On success, signal: `SELF-PUSHED ce-n15a-skip-anomaly <full-40-hex-sha> PR=<number>`

**Fallback:** if the broker socket is unreachable or the push fails with a non-policy error
(socket not found, transport failure, unexpected 500), signal:
`READY-FOR-HARVEST ce-n15a-skip-anomaly <full-40-hex-sha>` and include the failure class
(e.g. `socket-unreachable`, `transport-500`) on the next line so the controller can triage.
A 403 `egress_refused` policy refusal is NOT a fallback trigger — resolve it (check that the
branch is freshly based on origin/main and carries both its changelog and its carrier).

**Supersession guard warning:** the broker's supersession check requires the branch to be freshly
based on current origin/main AND to carry the `.ce/changelog/ce-n15a-skip-anomaly.md` and
`.ce/pr-manifests/ce-n15a-skip-anomaly.md` files. A stale base or missing carrier causes a
policy-level 403 push refusal. Fetch origin and rebase before running the canary if any doubt
exists about the merge base.

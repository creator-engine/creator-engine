# BRIEF — dev-4 — 2026-07-09 — BATCH: approval-TTL re-mint + smoke uid fix + merge-group e2e

Role: **implementer**. Contained COMMIT-ONLY seat (ce-dgx-codex). No venv activation needed;
use the installed `ce`.

---

## BORN-A-FOREMAN EXECUTION MODEL

You drive three tickets concurrently: **one git worktree + background subagent-thread per
ticket**. All three threads may run simultaneously — the units are FILE-DISJOINT (see
disjointness analysis below). Report **PER-TICKET**: one READY or BLOCKED signal per unit
before your session ends. A unit that is BLOCKED does not block other units from signaling
READY. Never merge unit work across branches or worktrees. COMMIT EARLY AND OFTEN — runsc
worktrees are RAM-backed; OOM = total loss of in-progress work.

Signal format per unit:

```
READY <branch> <40-char-sha> <carrier-path>
BLOCKED <branch> <one-line reason>
```

---

## PREFLIGHT PRECONDITION — fetch first

Before starting any thread, run:

```bash
git fetch origin
git log origin/main --oneline | head -5
```

Confirm the head commit is `db07e6dc0638a8edfc72ace7fcc73a8d8b7d8060` (Add
Acceptance-Evidence autoclose gate, #916) or a later commit. If a newer commit has landed
since this brief was composed, proceed — use the actual current `origin/main` HEAD as the
base for all branches.

**Do not touch `.ce/brain/assertions.yaml` in any unit.** The brain-ledger tail is
serialized. If any gate in any unit demands a ledger append, write BLOCKED immediately
and stop that thread.

---

## DISJOINTNESS ANALYSIS (read before starting any thread)

**Unit A files** (approval-marker TTL re-mint):
- `validators/creator_engine_validator/forge/integrator_belt.py` (modify)
- `validators/tests/unit/test_integrator_belt.py` (extend)
- `.ce/changelog/ce-493-approval-marker-ttl-remint.md` (new)
- `.ce/pr-manifests/ce-493-approval-marker-ttl-remint.md` (new)
- `.ce/wt-493/READY` or `.ce/wt-493/BLOCKED` (signal)

**Unit B files** (smoke uid mismatch + log dump):
- `deploy/daemons/smoke-daemon-container.sh` (modify)
- `.ce/changelog/ce-492-smoke-uid-mismatch.md` (new)
- `.ce/pr-manifests/ce-492-smoke-uid-mismatch.md` (new)
- `.ce/wt-492/READY` or `.ce/wt-492/BLOCKED` (signal)

**Unit C files** (merge-group e2e fixture):
- `validators/tests/integration/test_adoption_merge_group_e2e.py` (new)
- `.ce/changelog/ce-461-merge-group-e2e.md` (new)
- `.ce/pr-manifests/ce-461-merge-group-e2e.md` (new)
- `.ce/wt-461/READY` or `.ce/wt-461/BLOCKED` (signal)

**Cross-batch dev-3 in-flight paths** (BRIEF_dev3_restock_batch_20260709.md):
`validators/tests/integration/test_release_finalize_integration.py`,
`.github/scripts/ceops_autoclose.py`,
`.github/workflows/ce-ops-autoclose.yml`,
`validators/tests/unit/test_p2_acceptance_evidence.py`

**Collision verdict:**
- Unit A vs Unit B: **CLEAR** — no shared files.
- Unit A vs Unit C: **CLEAR** — no shared files.
- Unit B vs Unit C: **CLEAR** — no shared files.
- Any unit vs dev-3 batch: **CLEAR** — no shared files.
- `assertions.yaml` is out-of-bounds for all units.

**Brain ledger gate (pre-authorized):**
`validators/creator_engine_validator/forge/integrator_belt.py` is an explicit evidence_ref
in `.ce/brain/assertions.yaml` (items 10/11/approval-gate assertions). The three
assertions backed by integrator_belt.py are:
- merge-queue-conflict-gate: conflict/repair failures escalate.
- approval-green-triggers-queue: current-head approval + green state triggers queue.
- approval-current-head-required: APPROVED review tied to current head required.

Unit A adds a re-mint path for the `expired` reason when a current-head review still
exists. This STRENGTHENS item 11 (approval-green-triggers-queue) — the re-mint ensures
valid approvals continue to trigger the queue even after TTL expiry. It does NOT remove
or weaken any asserted behavior. The gate-verification probes (`probe:integrator_belt_*`)
re-run dynamically at preflight time against the modified code and will remain GREEN. No
brain ledger append is required. Gate clear.

---

## STANDING OBLIGATIONS BLOCK — read this before writing any file

Every unit in this brief MUST deliver ALL of the following. Missing any one item is a
harvest blocker.

1. **Changelog fragment**: `.ce/changelog/<branch>.md` — one short paragraph describing
   what changed and why. No ce-ops# references in the text body (product lens).

2. **Carrier / path-manifest**: `.ce/pr-manifests/<branch>.md` — lists every changed path
   (including the changelog fragment itself). Must contain exactly **one** line of the form:
   ```
   - **Declared work class:** <XS|S|M|L>
   ```
   The carrier slug (filename stem) MUST equal the branch name exactly. Zero ce-ops# refs.

3. **Targeted in-seat tests only**: run only the test files touched by your unit. Full
   suite execution is prohibited in this seat environment (resource limits). The controller
   preflight on `origin/main` is authoritative for the full suite.

4. **Signal file**: write `.ce/wt-<ticket>/READY` or `.ce/wt-<ticket>/BLOCKED` as the
   FINAL commit on your branch before stopping.

5. **Commit early and often**: runsc worktrees are RAM-backed — an OOM event will wipe
   all in-progress work. Commit every meaningful increment (at minimum: after initial
   probe, after each item, before tests). Push-to-remote is not available; commits survive
   as long as the worktree exists and can be harvested via `git bundle`.

**Pre-authorized false-RED classes** (proven in this seat environment — if the ONLY
failures are these gates on files you did NOT touch, note them verbatim and signal READY):
- `control-plane portability` gate on paths outside your diff
- `check-examples` gate failures on paths outside your diff
- `libsodium` gate failures on paths outside your diff

Any failure touching YOUR changed files = fix or BLOCKED.

---

## UNIT A — approval-capability marker TTL re-mint on expiry

**Branch:** `ce-493-approval-marker-ttl-remint`
**Worktree:** `/var/tmp/wt-493`
**Work class:** S
**Carrier slug must match branch exactly:** `ce-493-approval-marker-ttl-remint`

### Ticket body (ce-ops#493 — embedded for offline access)

```
Title: queue-daemon: approval-capability marker TTL expiry during merge-queue retry loop
       permanently wedges approved PRs

State: OPEN | Labels: bug, triage:ready, wc:S

## Symptom

A PR with a valid GitHub review approval by the authorized reviewer (ce-dev-2) becomes
permanently stuck after one or more merge-queue CI failures. The queue-daemon logs
{"reason": "approval_capability_invalid", "evidence": ["approval_capability_reason=expired"],
"status": "skip"} on every subsequent pass and never re-enqueues. A fresh human re-approval
only buys one more enqueue attempt before the marker expires again.

## Mechanics

1. Controller approves a PR → approval-capability marker minted in PR body (TTL: 600 s).
2. Daemon enqueues PR into GitHub merge queue.
3. merge_group CI run fails → GitHub dequeues the PR (~7–8 min round trip, longer than TTL).
4. On the next daemon pass the marker's embedded expiry has elapsed → daemon evaluates
   reason "expired" → logs approval_capability_invalid + skips.
5. No re-mint path for the "expired" reason — only "approval_capability_missing" triggers
   re-mint. The underlying GitHub review approval is still valid; only the internal marker
   is stale.

## Evidence (live incidents)

- creator-engine#859 (2026-07-06): added_to_merge_queue / removed_from_merge_queue cycled
  8+ times across ~71 min; then entered skip-loop for ~9 additional hours.
- creator-engine#874 (2026-07-07 ~02:59Z): hit identical path on first dequeue.

## Root cause

_approval_marker_mint_needed (integrator_belt.py) treats "expired" as hard-skip rather
than a conditional re-mint trigger. This is correct for a forged/tampered marker but wrong
when the underlying reviewer approval on the current head is still valid.

## Proposed fix

When daemon finds approval_capability_reason=expired, re-run the same trusted-approval
check used for approval_capability_missing (verify a valid ce-dev-2 review exists on the
current head); if it passes, re-mint. Fail-closed if the review is absent or on a wrong
head. Add distinct log reasons: expired_review_valid vs expired_review_absent.

## Refs

- validators/creator_engine_validator/forge/integrator_belt.py
  (_approval_marker_mint_needed + skip branch)
- creator-engine#859 (incident PR, 2026-07-06)
- creator-engine#874 (incident PR, 2026-07-07)
```

### Problem statement (grounded in code on origin/main)

On `origin/main:db07e6dc0`, in
`validators/creator_engine_validator/forge/integrator_belt.py`:

```python
def _approval_marker_mint_needed(
    gate: DaemonGateEvaluation,
    approval_verifier: ApprovalCapabilityVerifier | None,
    approval_wall: ApprovalWallRuntime | None,
    approval_marker_issuer: ApprovalMarkerIssuer | None,
) -> bool:
    if gate.refusal_reason != "approval_capability_missing":
        return False            # <-- "expired" falls here: always returns False
    return _approval_marker_minting_available(...)
```

The function returns `False` for ALL reasons except `approval_capability_missing`. The
`head_mismatch` case has a separate handler (parallel to `mint_needed`) that RE-VALIDATES
approval on current head before setting `mint_needed = True`. The `expired` case has no
equivalent: it falls to the decision loop's `if gate.refusal_reason is not None: → skip`.

### Probe before editing

```bash
git show origin/main:validators/creator_engine_validator/forge/integrator_belt.py | \
  sed -n '1676,1695p'
# Expect: _approval_marker_mint_needed returns False for non-"missing" reasons.

git show origin/main:validators/creator_engine_validator/forge/integrator_belt.py | \
  grep -n "expired_review_valid\|expired_review_absent"
# Expect: zero hits — confirms the distinct reason values are not yet implemented.
```

If either probe shows the fix is already present, note `PROBE_A: already_resolved` in
the READY signal and confirm via acceptance criteria.

### Deliverable — one gate-adjacent change in integrator_belt.py

**CAUTION: This file is gate-adjacent. The change is NARROWLY SCOPED. Do not restructure
existing logic, remove existing conditions, or touch any non-expired path. Every edit
must be additive relative to current behavior.**

**Step 1:** Add a helper to detect the expired-but-review-valid case:

```python
def _approval_marker_expired_review_check(gate: DaemonGateEvaluation) -> bool:
    """True when the capability gate fired with reason=expired."""
    return (
        gate.refusal_reason == "approval_capability_invalid"
        and _approval_capability_invalid_reason(gate) == "expired"
    )
```

**Step 2:** In the main PR decision loop, parallel to the `head_mismatch_refusal` block
(look for the pattern `if head_mismatch_refusal:`), add an analogous block for
`expired_refusal`:

```python
        expired_refusal = _approval_marker_expired_review_check(gate)
        # ... (after the existing head_mismatch_refusal block and before the
        #      mint_needed check) ...
        if expired_refusal:
            trusted_witness, trusted_refusal = _trusted_current_approval_witness(pr, authorized)
            if trusted_witness is None:
                gate = DaemonGateEvaluation(
                    "approval_capability_invalid",
                    (*gate.evidence, "approval_capability_reason=expired_review_absent",
                     f"current_approval_reason={trusted_refusal}"),
                )
            elif _approval_marker_minting_available(
                approval_verifier,
                approval_wall,
                approval_marker_issuer,
            ):
                mint_needed = True
                gate = DaemonGateEvaluation(
                    None,
                    (*gate.evidence, "approval_capability_reason=expired_review_valid"),
                )
```

Insert this block AFTER the `head_mismatch_refusal` block and BEFORE the `if mint_needed:`
block. Use the exact same `_trusted_current_approval_witness` function the `head_mismatch`
path already calls — do not duplicate that logic.

**Step 3:** Tests in `validators/tests/unit/test_integrator_belt.py`

Add at minimum these two test cases:

```python
def test_expired_refusal_with_valid_review_sets_mint_needed(...):
    # Arrange: gate has reason=expired; a current-head review exists
    # Act: run the daemon decision loop (or the relevant sub-function)
    # Assert: mint_needed=True; gate reason is None (re-mint proceeds)

def test_expired_refusal_with_absent_review_keeps_skip(...):
    # Arrange: gate has reason=expired; no current-head review
    # Act: run the daemon decision loop
    # Assert: decision is "skip"; evidence contains "expired_review_absent"
```

Use the same fake/stub approach as existing tests in `test_integrator_belt.py`. Check
the existing patterns (`FakeApprovalWall`, `FakeApprovalVerifier`, or equivalent) to
match the test style consistently.

### Acceptance criteria

1. `grep -n "expired_refusal\|expired_review_valid\|expired_review_absent" \
   validators/creator_engine_validator/forge/integrator_belt.py`
   returns hits for all three tokens (or `PROBE_A: already_resolved`).
2. `grep -n "_approval_marker_expired_review_check" \
   validators/creator_engine_validator/forge/integrator_belt.py` returns a hit.
3. `pytest validators/tests/unit/test_integrator_belt.py -v` passes with new test cases
   present.
4. `ce validate-pr --profile contained-seat` green on the diff.
5. `ARMING_ENABLED` value in `integrator_belt.py` is UNCHANGED from `origin/main`
   (verify: `grep ARMING_ENABLED validators/creator_engine_validator/forge/integrator_belt.py`).

### Hard constraints

- GATE-ADJACENT: do NOT change any gating behavior for the `head_mismatch_refusal`,
  `approval_capability_missing`, or any other non-expired path.
- Do NOT touch `ARMING_ENABLED` — this is a bug fix, not an arming act.
- Do NOT touch `conveyor_daemon_runner.py`, `brain_intent_materializer.py`, or any file
  outside the STOP LINE.
- Do NOT touch `.ce/brain/assertions.yaml`.
- The re-mint path MUST be fail-closed: if `_trusted_current_approval_witness` returns
  `None` (no valid review), the PR remains skipped with reason `expired_review_absent`.

### STOP LINE (Unit A)

No pushes, no PRs, no gate acts. Only these paths:

```
validators/creator_engine_validator/forge/integrator_belt.py
validators/tests/unit/test_integrator_belt.py
.ce/changelog/ce-493-approval-marker-ttl-remint.md
.ce/pr-manifests/ce-493-approval-marker-ttl-remint.md
.ce/wt-493/READY
.ce/wt-493/BLOCKED
```

Carrier: slug `ce-493-approval-marker-ttl-remint` exactly; every changed path listed;
exactly ONE `- **Declared work class:** S` line.

### READY / BLOCKED signals (Unit A)

**When DONE — write `.ce/wt-493/READY` then emit:**
```
STATUS: READY
BRANCH: ce-493-approval-marker-ttl-remint
COMMIT: <HEAD SHA after final commit>
CARRIER: .ce/pr-manifests/ce-493-approval-marker-ttl-remint.md
PROBE_A: <open|already_resolved>
ARMING_ENABLED_VALUE: <value from grep on modified file>
VALIDATE_PR: GREEN
GATE_NOISE: <"none" or verbatim text of false-RED gates on untouched files>
READY ce-493-approval-marker-ttl-remint <sha> .ce/pr-manifests/ce-493-approval-marker-ttl-remint.md
```
Commit the signal file as the FINAL commit on the branch before stopping.

**When BLOCKED — write `.ce/wt-493/BLOCKED` then emit:**
```
STATUS: BLOCKED
BRANCH: ce-493-approval-marker-ttl-remint
BLOCKER: <one-sentence description>
CONTEXT: <full context, file/line/error>
BLOCKED ce-493-approval-marker-ttl-remint <reason>
```

---

## UNIT B — smoke-daemon-container.sh uid mismatch + observability fix

**Branch:** `ce-492-smoke-uid-mismatch`
**Worktree:** `/var/tmp/wt-492`
**Work class:** XS
**Carrier slug must match branch exactly:** `ce-492-smoke-uid-mismatch`

### Ticket body (ce-ops#492 — embedded for offline access)

```
Title: bug: smoke-daemon-container.sh pass-1 lease wait fails under rootful Docker —
       write_secret_file uid mismatch + failure log swallowed on cleanup

State: OPEN | Labels: bug, triage:ready, wc:S

## Symptom

deploy/daemons/smoke-daemon-container.sh times out with:
  "timed out waiting for pass 1 conveyor lease"
under rootful Docker on DGX (aarch64, spark-b824, uid=cedev2/1003). The actual root
cause is invisible in the smoke output.

## Root cause

write_secret_file creates the conveyor signing secret file as 0600 owned by the invoking
host user (uid 1003 on DGX). The adapter bind-mounts that file :ro into the container
where the daemon runs as uid 10001. The daemon cannot read it.

This does NOT reproduce under rootless Podman (the validation-tier engine used by CI)
because Podman's uid-namespace mapping transparently shifts ownership, so CI is blind to
this failure mode.

## Observability gap

The smoke script redirects per-pass container output to a mktemp tmpdir and rm -rf-s it
in the failure-path cleanup handler BEFORE surfacing the timeout message. The probe phase
already dumps its log to stderr on failure; the pass phase does not. It took 4 re-runs
with manual extraction to isolate the root cause.

## Evidence

- /var/tmp/c5-smoke*.log on DGX (spark-b824) — produced 2026-07-06.
- Manual smoke with chown 10001:10001 applied to the signing secret: GREEN.

## Proposed fix

(a) write_secret_file: apply chown <CE_DAEMON_IMAGE_UID>:<CE_DAEMON_IMAGE_UID> after
writing the secret file. For rootless Podman this is a no-op (uid-mapping handles it).

(b) Smoke script cleanup: emit per-pass log to stderr before rm -rf of tmpdir on any
exit path (including wait_for_file timeout → die → EXIT trap), mirroring the probe-phase
behavior already present.

## Refs

- deploy/daemons/smoke-daemon-container.sh
- creator-engine PR#853 — shipped stateful smoke (this file's prior fix)
```

### Problem statement (grounded in code on origin/main)

On `origin/main:db07e6dc0`, in `deploy/daemons/smoke-daemon-container.sh`:

**Gap (a) — `write_secret_file`** (line ~120):
```bash
write_secret_file() {
  local path="$1"
  umask 077
  printf '%s\n' "$SMOKE_SECRET_VALUE" > "$path"
  chmod 0600 "$path"
  # MISSING: chown ${CE_DAEMON_IMAGE_UID}:${CE_DAEMON_IMAGE_UID} "$path"
}
```
The file is always owned by the invoking host user (uid 1003 on DGX). The container
daemon runs as uid 10001 (the `CE_DAEMON_IMAGE_UID` default). Under rootful Docker the
container cannot read a 0600 file owned by a different uid.

**Gap (b) — `cleanup()`** (line ~239):
```bash
cleanup() {
  stop_current_container
  [[ -z "$SMOKE_TMPDIR" ]] || rm -rf -- "$SMOKE_TMPDIR"
}
```
When `wait_for_file` times out, `die` is called immediately (triggering the EXIT trap →
`cleanup()`). The `rm -rf "$SMOKE_TMPDIR"` deletes the pass log before any human can see
it. The log-dump-on-failure path in `run_pass` (lines ~280-284) only fires when the
runner subprocess itself fails, not on a timeout.

### Probe before editing

```bash
grep -n "chown" deploy/daemons/smoke-daemon-container.sh | head -5
# Expect: no chown in write_secret_file (confirms gap a is open)

grep -n "SMOKE_TMPDIR" deploy/daemons/smoke-daemon-container.sh | head -10
# Confirms the cleanup function and any existing tmpdir reference patterns
```

If either probe shows the fix is already present, note `PROBE_B<n>: already_resolved`.

### Deliverable — two changes in smoke-daemon-container.sh

**Fix (a): Add chown to `write_secret_file`**

```bash
write_secret_file() {
  local path="$1"
  umask 077
  printf '%s\n' "$SMOKE_SECRET_VALUE" > "$path"
  chmod 0600 "$path"
  # Rootful Docker: host uid != container uid; chown to image uid so the daemon
  # can read the secret. Under rootless Podman the uid-namespace mapping makes
  # this a no-op (effective host uid equals mapped container uid).
  if [[ -n "${CE_DAEMON_IMAGE_UID:-}" ]]; then
    chown "${CE_DAEMON_IMAGE_UID}:${CE_DAEMON_IMAGE_UID}" "$path" 2>/dev/null || true
  fi
}
```

Use `|| true` to ensure the chown failure (e.g., when running as non-root on a system
that rejects cross-uid chown) does not abort the script. The subsequent `wait_for_file`
timeout will surface the access failure clearly.

**Fix (b): Dump pass logs in `cleanup()` before deleting tmpdir**

```bash
cleanup() {
  stop_current_container
  # Dump any captured pass logs to stderr before deleting the tmpdir so that
  # timeout-triggered exits (die() → EXIT trap) surface the root cause.
  if [[ -n "$SMOKE_TMPDIR" && -d "$SMOKE_TMPDIR" ]]; then
    for _log in "$SMOKE_TMPDIR"/smoke-pass-*.log; do
      [[ -f "$_log" ]] || continue
      local _label
      _label="$(basename "$_log" .log)"
      printf '%s\n' "---- $_label log (cleanup dump) ----" >&2
      sed -n '1,220p' "$_log" >&2 || true
    done
  fi
  [[ -z "$SMOKE_TMPDIR" ]] || rm -rf -- "$SMOKE_TMPDIR"
}
```

The loop pattern `smoke-pass-*.log` matches the filenames written by `run_pass`
(`"$tmpdir/smoke-pass-$pass.log"`). The `sed -n '1,220p'` mirrors the existing dump
pattern already used in `run_pass` and the probe-phase failure path.

Note: `local _label` inside a function after `set -euo pipefail` can cause issues in
some bash versions if the assignment fails. Use `local _label; _label=...` or a bare
assignment. Probe the bash version in the seat (`bash --version`) and adjust if needed.

### Acceptance criteria

1. `grep -n "chown" deploy/daemons/smoke-daemon-container.sh | grep "write_secret_file" \
   -A5` — or more precisely: `sed -n '/write_secret_file/,/^}/p' \
   deploy/daemons/smoke-daemon-container.sh | grep "chown"` returns a hit.
2. `grep -n "cleanup dump\|smoke-pass" deploy/daemons/smoke-daemon-container.sh`
   returns a hit inside `cleanup()`.
3. `bash -n deploy/daemons/smoke-daemon-container.sh` exits 0 (syntax check).
4. `ce validate-pr --profile contained-seat` green on the diff.

No new test file required — bash scripts are validated by syntax check only in this
seat environment. The fix is verified at next C5 cutover.

### Hard constraints

- Do NOT change `run_pass`, `wait_for_file`, `die`, `assert_docker_state_owned_by_image_uid`,
  `run_mixed_uid_host_prep_probe`, or any other function except `write_secret_file` and
  `cleanup`.
- Do NOT touch `.ce/brain/assertions.yaml`.
- The `|| true` on chown is intentional — do not omit it.

### STOP LINE (Unit B)

No pushes, no PRs, no gate acts. Only these paths:

```
deploy/daemons/smoke-daemon-container.sh
.ce/changelog/ce-492-smoke-uid-mismatch.md
.ce/pr-manifests/ce-492-smoke-uid-mismatch.md
.ce/wt-492/READY
.ce/wt-492/BLOCKED
```

Carrier: slug `ce-492-smoke-uid-mismatch` exactly; every changed path listed; exactly
ONE `- **Declared work class:** XS` line.

### READY / BLOCKED signals (Unit B)

**When DONE — write `.ce/wt-492/READY` then emit:**
```
STATUS: READY
BRANCH: ce-492-smoke-uid-mismatch
COMMIT: <HEAD SHA after final commit>
CARRIER: .ce/pr-manifests/ce-492-smoke-uid-mismatch.md
PROBE_Ba: <open|already_resolved>
PROBE_Bb: <open|already_resolved>
SYNTAX_CHECK: <pass|fail>
VALIDATE_PR: GREEN
GATE_NOISE: <"none" or verbatim text of false-RED gates on untouched files>
READY ce-492-smoke-uid-mismatch <sha> .ce/pr-manifests/ce-492-smoke-uid-mismatch.md
```
Commit the signal file as the FINAL commit on the branch before stopping.

**When BLOCKED — write `.ce/wt-492/BLOCKED` then emit:**
```
STATUS: BLOCKED
BRANCH: ce-492-smoke-uid-mismatch
BLOCKER: <one-sentence description>
CONTEXT: <full context, file/line/error>
BLOCKED ce-492-smoke-uid-mismatch <reason>
```

---

## UNIT C — adoption merge-group e2e fixture

**Branch:** `ce-461-merge-group-e2e`
**Worktree:** `/var/tmp/wt-461`
**Work class:** S
**Carrier slug must match branch exactly:** `ce-461-merge-group-e2e`

### Ticket body (ce-ops#461 — embedded for offline access)

```
Title: e2e fixture for validate-pr merge-group parity (respawned from #428c)

State: OPEN | Labels: triage:ready, wc:S

## Context

Part (c) respawned from ce-ops#428: adoption e2e test against a NON-CE-shaped fixture
repo.

ce-ops#428 parts (a) and (b) delivered by PRs #830 and #834. Part (c) remains as its
own work unit: verify the product fix (workflow template + client-repo profile) with a
real non-CE-shaped client repo fixture through the full adoption+CI lifecycle (merge-group
parity test).

Prior blocker: ce-ops#473 (adoption workflow template lacked merge_group trigger). That
fix is now on origin/main via PR #859 (merged 2026-07-07).

## Related

- ce-ops#428 (parent), ce-ops#421 (tenant adoption)
- ce-ops#473 (prerequisite): CLOSED via PR #859 (merge_group trigger now in onboard_apply.py)
```

### Problem statement (grounded in code on origin/main)

PR #859 (merged 2026-07-07) added `merge_group: types: [checks_requested]` to the
`CE_WORKFLOW_TEMPLATE` in `validators/creator_engine_validator/onboard_apply.py`, and
added a UNIT test (`test_ce_workflow_template_triggers_on_merge_group_checks_requested` in
`validators/tests/unit/test_onboard_apply.py`) that parses the template and asserts the
trigger stanza.

What remains is the E2E validation: exercising the FULL ADOPTION PATH (not just the
template string) against a **non-CE-shaped fixture repo** and asserting merge-group parity
end-to-end. "Non-CE-shaped" means the fixture repo does NOT already have `ce-validate.yml`
present before adoption.

A stale claim (`ce-461-adoption-e2e-fixture`, dispatched 2026-07-06 to dev-3) was
abandoned before delivery when the prerequisite (ce-ops#473) was unresolved. That branch
does not exist on the remote. This unit delivers the fixture under a fresh branch.

### Probe before editing

```bash
# Confirm the prior claim branch is not present on the remote
git ls-remote origin | grep "ce-461"
# Expect: no hits (confirms fresh start)

# Confirm the onboard_apply template has the trigger on origin/main
git show origin/main:validators/creator_engine_validator/onboard_apply.py | \
  grep -A2 "merge_group"
# Expect: merge_group:\n  types: [checks_requested]

# Confirm no existing e2e file for adoption merge-group
git show origin/main:validators/tests/integration/test_adoption_merge_group_e2e.py 2>&1 | head -3
# Expect: fatal: Path does not exist — confirms new file
```

If any probe shows the test already exists, note `PROBE_C: already_resolved`.

### Deliverable — one new integration test file

Create `validators/tests/integration/test_adoption_merge_group_e2e.py`.

The test exercises the adoption workflow (specifically the workflow-template emission
path in `onboard_apply.py`) with a minimal non-CE-shaped fixture repo and asserts:

1. After adoption apply, the emitted workflow contains `merge_group: types: [checks_requested]`.
2. The emitted workflow trigger stanza matches the parity expectation against CE's own
   `.github/workflows/validate.yml` (the canonical trigger shape).
3. The emitted workflow does NOT contain CE-internal references (no paths under
   `validators/`, no `CE_WORKFLOW_TEMPLATE` marker string, no internal tool invocations).

**Implementation approach:**

Use the `FakeDriver` pattern from `validators/tests/unit/test_onboard_apply.py` — import
`FakeDriver` (or its refactored equivalent) and drive `onboard_apply.apply()` with a
minimal fixture dict representing a non-CE-shaped brownfield repo. The fixture should
have:
- `repo_exists: True`
- `workflow_present: False` (no existing ce-validate.yml — the non-CE-shaped condition)
- `ci_workflows: []` (no current CI workflows)

After `apply()`, inspect the call record to extract the content passed to
`install_workflow()` and parse it with `yaml.safe_load()` to assert the trigger stanza.

Minimal test structure (adjust to match live `onboard_apply.apply()` signature on
`origin/main` — probe it before writing):

```python
"""E2e parity test: adoption workflow emitted into non-CE-shaped fixture repos
must include the merge_group trigger matching CE's own validate workflow."""
from __future__ import annotations

import yaml
import pytest
from pathlib import Path

pytestmark = pytest.mark.slow

REPO_ROOT = Path(__file__).resolve().parents[3]
CE_VALIDATE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "validate.yml"


def _parse_workflow_triggers(workflow_yaml: str) -> dict:
    data = yaml.safe_load(workflow_yaml)
    return data.get("on", {}) if isinstance(data, dict) else {}


def test_adoption_workflow_merge_group_parity_non_ce_shaped(tmp_path):
    """Non-CE-shaped fixture repo: adoption must emit a workflow containing
    the merge_group trigger matching CE's own validate.yml."""
    # 1. Probe the canonical trigger from CE's own workflow.
    ce_triggers = _parse_workflow_triggers(CE_VALIDATE_WORKFLOW.read_text())
    assert "merge_group" in ce_triggers, (
        "CE's own validate.yml lacks merge_group trigger — test precondition failed"
    )

    # 2. Drive adoption against the non-CE-shaped fixture.
    #    Import FakeDriver and related machinery from test_onboard_apply.
    from tests.unit.test_onboard_apply import FakeDriver, _minimal_answers  # adjust import
    driver = FakeDriver(repo_exists=True, workflow_present=False)
    answers = _minimal_answers(tmp_path)
    from creator_engine_validator.onboard_apply import apply
    apply(answers, driver=driver)

    # 3. Verify the workflow that was installed.
    installed = driver.installed_workflow_content
    assert installed is not None, "adoption apply did not call install_workflow"
    emitted_triggers = _parse_workflow_triggers(installed)
    assert "merge_group" in emitted_triggers, (
        f"emitted workflow lacks merge_group trigger; got triggers: {list(emitted_triggers)}"
    )
    assert emitted_triggers["merge_group"] == {"types": ["checks_requested"]}, (
        f"emitted merge_group trigger does not match canonical shape; got: {emitted_triggers['merge_group']}"
    )

    # 4. Parity assertion: emitted trigger stanza matches CE's own.
    assert emitted_triggers.get("merge_group") == ce_triggers.get("merge_group"), (
        "merge_group trigger in emitted workflow does not match CE's own validate.yml"
    )

    # 5. No CE-internal references in the emitted workflow.
    assert "CE_WORKFLOW_TEMPLATE" not in installed
    assert "validators/" not in installed
```

**Important:** Before writing this file, probe the exact `FakeDriver` API and
`onboard_apply.apply()` signature on `origin/main`:

```bash
git show origin/main:validators/tests/unit/test_onboard_apply.py | \
  grep -n "class FakeDriver\|def apply\|installed_workflow\|install_workflow" | head -20
git show origin/main:validators/creator_engine_validator/onboard_apply.py | \
  grep -n "^def apply\|^class.*apply" | head -5
```

Adjust the test structure to match the live API. If `FakeDriver` is not importable from
the integration test directory, reproduce the minimal fake inline in the new file (keeping
it under 40 lines).

### Acceptance criteria

1. `pytest validators/tests/integration/test_adoption_merge_group_e2e.py -v` passes
   (or note `PROBE_C: already_resolved` and point to the existing test).
2. The test asserts `merge_group` in the emitted workflow triggers AND parity with
   CE's own `.github/workflows/validate.yml`.
3. `ce validate-pr --profile contained-seat` green on the diff.

### Hard constraints

- Do NOT touch `validators/creator_engine_validator/onboard_apply.py` or any production
  module — this is a TEST-ONLY unit.
- Do NOT touch `validators/tests/unit/test_onboard_apply.py` — read it but do not modify.
- Do NOT touch `.ce/brain/assertions.yaml`.
- `pytestmark = pytest.mark.slow` must be present (integration tests are slow-marked).
- If `FakeDriver` cannot be cleanly imported from the unit test module, reproduce a
  minimal inline fake rather than restructuring the import graph.

### STOP LINE (Unit C)

No pushes, no PRs, no gate acts. Only these paths:

```
validators/tests/integration/test_adoption_merge_group_e2e.py
.ce/changelog/ce-461-merge-group-e2e.md
.ce/pr-manifests/ce-461-merge-group-e2e.md
.ce/wt-461/READY
.ce/wt-461/BLOCKED
```

Carrier: slug `ce-461-merge-group-e2e` exactly; every changed path listed; exactly ONE
`- **Declared work class:** S` line.

### READY / BLOCKED signals (Unit C)

**When DONE — write `.ce/wt-461/READY` then emit:**
```
STATUS: READY
BRANCH: ce-461-merge-group-e2e
COMMIT: <HEAD SHA after final commit>
CARRIER: .ce/pr-manifests/ce-461-merge-group-e2e.md
PROBE_C: <open|already_resolved>
FAKE_DRIVER_APPROACH: <"imported" | "inline_fake: <N> lines">
VALIDATE_PR: GREEN
GATE_NOISE: <"none" or verbatim text of false-RED gates on untouched files>
READY ce-461-merge-group-e2e <sha> .ce/pr-manifests/ce-461-merge-group-e2e.md
```
Commit the signal file as the FINAL commit on the branch before stopping.

**When BLOCKED — write `.ce/wt-461/BLOCKED` then emit:**
```
STATUS: BLOCKED
BRANCH: ce-461-merge-group-e2e
BLOCKER: <one-sentence description>
CONTEXT: <full context, file/line/error>
BLOCKED ce-461-merge-group-e2e <reason>
```

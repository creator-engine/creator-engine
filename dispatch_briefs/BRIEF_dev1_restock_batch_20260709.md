# BRIEF — dev-1 — 2026-07-09 — Restock Batch: ce-501-queue-canary + ce-502-standby-surface

**Role:** implementer. SELF-PUSH seat (dev-1 is the non-contained VPS host seat — codex TUI
in tmux, repo at `~/creator-engine`, has own GitHub identity, self-push capable). Open PRs
**NOT as drafts** — ready-for-review from the start (born-draft defect stalled #905; do not
repeat it). Signal each unit with `PR <number> <branch>` in the pane on open, or
`BLOCKED <branch> <reason>` on stop-lines.

**Origin/main ground SHA:** `add00a60e670ccf37e985576e2fd0240b54e4974`
(feat(review-daemon): review-pickup dry-run daemon slice 1 — PR #917, merged 2026-07-09)

Before starting EITHER unit, confirm ground:
```bash
git fetch origin
git log origin/main --oneline | head -3
```
The commit `add00a60e` must appear at the top. If it does not, re-fetch and do not proceed
until it does.

Auth for gh operations:
```bash
set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT
```

---

## BRAIN-ASSERTION FREEZE (applies to ALL units in this batch)

`.ce/brain/assertions.yaml` is **exclusively claimed by PR #918 (ce-hermes-retirement,
currently in review)**. Do NOT append, modify, or supersede any ledger record in either
unit. If `ce validate-pr` or any gate demands a new brain assertion, write a BLOCKED signal:

```
BLOCKER: brain-ledger busy — PR #918 holds exclusive territory on .ce/brain/assertions.yaml
GATE: BRAIN-LEDGER-BUSY
```

No unit in this batch may touch `.ce/brain/assertions.yaml`.

---

## UNIT U1 — ce-501-queue-canary

**Branch:** `ce-501-queue-canary`
**Worktree:** `~/creator-engine-ce-501-queue-canary` (off `origin/main`)
**Ticket:** ce-ops#501
**Work class:** S

### Worktree setup

```bash
git fetch origin
git worktree add ~/creator-engine-ce-501-queue-canary -b ce-501-queue-canary origin/main
cd ~/creator-engine-ce-501-queue-canary
```

---

### Full ticket body (ce-ops#501)

> **title:** [gap] launch-queue-daemon.sh cannot start a canary (dry-run + dormant wall) —
> hardwired openbao backend forces configured_backend_without_secret refusal
>
> **labels:** triage:ready, wc:S
>
> ## Symptom
>
> `deploy/queue-daemon/launch-queue-daemon.sh` hardwires `--approval-wall-secret-backend
> openbao` and its `validate_required_env` demands `BAO_TOKEN`, `BAO_ADDR`, and a
> secret-path env var. A canary instance (dry-run + dormant wall) therefore cannot be
> launched through the canonical launcher: the approval-wall runtime code in
> `v3_cli.py _approval_wall_runtime_from_args` sees a configured backend without fetchable
> secrets and refuses `configured_backend_without_secret` (fail-closed). This is the correct
> posture for the live gate; it is a blocker for canaries.
>
> ## Evidence
>
> Tonight's D3 shadow-canary set-piece (`.ce/state/research/D3_SHADOW_CANARY_REPORT_20260708.md`
> in the creator-engine repo) ran successfully and produced a GREEN decision-parity result
> vs the live daemon across a ~45-minute window. But it required a **direct daemon invocation**
> bypassing the launcher entirely — exactly the session-workaround anti-pattern CE codifies
> away. The report notes explicitly: "GAP TICKETED."
>
> Concrete launcher path: `deploy/queue-daemon/launch-queue-daemon.sh` → passes
> `--approval-wall-secret-backend openbao` unconditionally → `_approval_wall_runtime_from_args`
> in `v3_cli.py` resolves backend to openbao → demands `BAO_TOKEN` + `BAO_ADDR` + secret path
> → absent any of them → raises `configured_backend_without_secret`.
>
> ## Root cause
>
> The launcher was written to serve ONE mode: the armed live gate with a full OpenBao credential
> set. There is no canary/dry-run lane that legitimately needs no wall secret (because DORMANT
> is the correct zero-authority posture, not a misconfiguration).
>
> ## Impact
>
> - Any future shadow-canary or pre-arm validation run must bypass the canonical launcher,
>   accumulating undocumented session workarounds.
> - Operator cannot delegate "spin up a dry-run canary" to a worker without also handing over
>   BAO credentials, conflating zero-authority testing with the live secret trust boundary.
> - Canary-as-set-piece (the D3 model) cannot be codified into a runbook that uses the
>   standard launcher.
>
> ## Proposed fix: `CE_QUEUE_DAEMON_CANARY=1` mode in the launcher
>
> When `CE_QUEUE_DAEMON_CANARY=1` is set:
>
> 1. **Imply `--dry-run`** — no `gh pr merge` calls can occur.
> 2. **Omit all `--approval-wall-secret-*` flags** — no backend is configured, wall resolves
>    to DORMANT legitimately (`secret_not_configured`).
> 3. **Relax `validate_required_env`** to only `GH_TOKEN` + `CE_GATE_REPO` +
>    `CE_GATE_AUTHORIZED_REVIEWERS` (the minimum for read-only forge observation).
> 4. **Require an isolated `CE_DAEMON_STATE_ROOT`** — refuse to start if it equals the live
>    daemon's default state root (prevent lease collision).
> 5. Emit a visible startup banner:
>    `CANARY MODE — dry_run=true, wall=dormant, no merge authority`.
>
> **Acceptance criterion**: a canary launches via `launch-queue-daemon.sh CE_QUEUE_DAEMON_CANARY=1`
> with a read-only forge token and zero BAO env vars, and its `daemon_pass_start` logs include
> `dry_run=true` and wall posture `dormant`.
>
> ## Refs
>
> - Evidence: `.ce/state/research/D3_SHADOW_CANARY_REPORT_20260708.md` (creator-engine repo,
>   controller state root)
> - Affected file: `deploy/queue-daemon/launch-queue-daemon.sh`
> - Runtime gate: `v3_cli.py` → `_approval_wall_runtime_from_args` →
>   `configured_backend_without_secret`
> - Related closed: #445 (queue-daemon container gaps on DGX)

---

### Scope — U1

**What changes:**

**1. `deploy/queue-daemon/launch-queue-daemon.sh`** (modify existing)

Add `CE_QUEUE_DAEMON_CANARY=1` mode. Implementation guidance:

- At the top of `validate_required_env` (or via a new `validate_required_env_canary`
  function called when `CE_QUEUE_DAEMON_CANARY=1`): only require `GH_TOKEN`,
  `CE_GATE_REPO`, and `CE_GATE_AUTHORIZED_REVIEWERS`. Do NOT call `require_env` on any
  `BAO_*` or `CE_APPROVAL_WALL_*` vars.
- Add a `canary_state_root_isolation_check` function: compare `CE_DAEMON_STATE_ROOT` (when
  set) against the live daemon default. If they are equal (or if `CE_DAEMON_STATE_ROOT` is
  unset and would default to the live root), emit an error and exit 1.
  Default live root to detect: `/var/lib/ce-queue-daemon/v3` (the `--root` default in
  `main_uncontained`). Canary must use a distinct path.
- In `main_uncontained`, before building `args`, add:
  ```bash
  if [[ "${CE_QUEUE_DAEMON_CANARY:-0}" == "1" ]]; then
    canary_state_root_isolation_check
    printf 'CANARY MODE — dry_run=true, wall=dormant, no merge authority\n' >&2
    args+=(--dry-run)
    # omit all --approval-wall-secret-* flags
    # use only minimal required args already present
  fi
  ```
  When in canary mode, skip the entire `--approval-wall-secret-backend openbao` block and
  all associated `--approval-wall-secret-*` arguments. The absence of these flags causes
  `_approval_wall_runtime_from_args` in `v3_cli.py` to resolve to DORMANT
  (`secret_not_configured`) — no Python changes are needed.
- The canary DOES still use `exec_with_queue_daemon_lease` (singleton lease is still
  required to prevent accidental double-canary — but with a distinct `CE_DAEMON_STATE_ROOT`
  the lease root will be isolated too).
- The `--health` sub-command must detect canary mode and adjust: skip `check_bao_token`
  when `CE_QUEUE_DAEMON_CANARY=1`.

**2. `validators/tests/unit/test_queue_daemon_canary_launch.py`** (new)

Write pytest tests that exercise the canary mode by invoking
`deploy/queue-daemon/launch-queue-daemon.sh` via `subprocess` (similar to the pattern in
`test_dgx_runsc.py`). Required test cases at minimum:

- `test_canary_mode_requires_no_bao_vars`: set only `GH_TOKEN`, `CE_GATE_REPO`,
  `CE_GATE_AUTHORIZED_REVIEWERS`, `CE_QUEUE_DAEMON_CANARY=1`, and a distinct
  `CE_DAEMON_STATE_ROOT`. Mock the Python invocation so it exits 0. Verify the script
  reaches the exec stage without exiting 1 on a missing-BAO error.
- `test_canary_mode_emits_banner`: verify `CANARY MODE — dry_run=true` appears in stderr.
- `test_canary_mode_refuses_shared_state_root`: set `CE_DAEMON_STATE_ROOT=/var/lib/ce-queue-daemon/v3`
  (the live default), set `CE_QUEUE_DAEMON_CANARY=1`. Verify exit != 0 and an error about
  state root collision appears in stderr.
- `test_non_canary_mode_still_requires_bao`: verify that without `CE_QUEUE_DAEMON_CANARY=1`,
  the launcher still exits non-zero when `BAO_TOKEN` is absent (regression guard).

Test location: `validators/tests/unit/test_queue_daemon_canary_launch.py`.

---

### Stop line — U1

No pushes, no PRs, no edits outside these paths:

```
deploy/queue-daemon/launch-queue-daemon.sh
validators/tests/unit/test_queue_daemon_canary_launch.py
.ce/changelog/ce-501-queue-canary.md
.ce/pr-manifests/ce-501-queue-canary.md
.ce/wt-ce501/READY
.ce/wt-ce501/BLOCKED
```

Absolute stop-lines — do NOT touch, even if a gate raises noise:
- `.ce/brain/assertions.yaml` (PR #918 exclusive territory)
- `deploy/vps-runsc/run-vps-runsc.sh` (PR #918)
- `deploy/dgx-runsc/run-codex-runsc.sh` (PR #918)
- `validators/creator_engine_validator/ce_cli.py` (PR #918)
- `validators/creator_engine_validator/v3_cli.py` (no changes needed; if gate demands a
  Python change here, signal BLOCKED)
- `deploy/daemons/smoke-daemon-container.sh` (dev-4 in-flight)
- Any file in dev-3 or dev-4 territory (listed in brief header)

If `ce validate-pr` raises a gate on a file OUTSIDE your diff, report it verbatim in the
READY signal under `GATE_NOISE` — do NOT touch it to silence it.

---

### Acceptance criteria — U1

U1 is complete when ALL of the following hold:

1. `deploy/queue-daemon/launch-queue-daemon.sh` has `CE_QUEUE_DAEMON_CANARY=1` mode:
   - Skips BAO env var requirements
   - Implies `--dry-run`
   - Omits all `--approval-wall-secret-*` CLI flags
   - Refuses if `CE_DAEMON_STATE_ROOT` equals the live default
   - Emits banner to stderr
2. `pytest validators/tests/unit/test_queue_daemon_canary_launch.py -v` passes (all 4
   required cases green).
3. Full `ce validate-pr` GREEN on the working tree.
4. Changelog fragment `.ce/changelog/ce-501-queue-canary.md` present.
5. Carrier `.ce/pr-manifests/ce-501-queue-canary.md` present with `slug: ce-501-queue-canary`,
   all changed paths listed, exactly one `- **Declared work class:** S` line, zero ce-ops#
   references.
6. PR opened (non-draft) on `ce-501-queue-canary`, PR body carries `- **Declared work class:** S`.
7. Signal file `.ce/wt-ce501/READY` written and committed as the FINAL commit.

---

### Standing obligations — U1

**Changelog** — `.ce/changelog/ce-501-queue-canary.md`:

```markdown
## ce-501-queue-canary

- feat(queue-daemon): add CE_QUEUE_DAEMON_CANARY=1 mode to launch-queue-daemon.sh

  When CE_QUEUE_DAEMON_CANARY=1 is set: implies --dry-run, omits all
  --approval-wall-secret-* flags (wall resolves DORMANT legitimately), relaxes
  required-env to GH_TOKEN + CE_GATE_REPO + CE_GATE_AUTHORIZED_REVIEWERS,
  refuses if CE_DAEMON_STATE_ROOT conflicts with the live daemon default,
  and emits a visible CANARY MODE banner. Closes ce-ops#501.

  - **Declared work class:** S
```

**Carrier** — `.ce/pr-manifests/ce-501-queue-canary.md`:
- `slug: ce-501-queue-canary`
- List ALL changed paths (including changelog, carrier itself, signal file)
- Exactly one `- **Declared work class:** S` line
- Zero ce-ops# references anywhere in the file

**Preflight** — dev-1 is a host seat; full `ce validate-pr` is expected. Run:
```bash
cd ~/creator-engine-ce-501-queue-canary
pytest validators/tests/unit/test_queue_daemon_canary_launch.py -v
ce validate-pr
```
Both must be green before self-push.

**PR body** must include:
1. `- **Declared work class:** S` (exactly once, verbatim)
2. Pytest result summary for `test_queue_daemon_canary_launch.py`
3. Reference to the D3 shadow-canary report gap that motivated the fix (no ce-ops# ref —
   describe it as: "closes the launcher gap noted in the D3 shadow-canary set-piece report")
4. `GATE_NOISE: <none or verbatim>` if validate-pr raised gates outside your diff

---

### READY / BLOCKED signals — U1

**When DONE — write `.ce/wt-ce501/READY` and commit as the final commit:**
```
STATUS: READY
BRANCH: ce-501-queue-canary
COMMIT: <HEAD SHA>
PR: <number>
CANARY_MODE_BANNER_TEST: PASS
STATE_ROOT_ISOLATION_TEST: PASS
BAO_REGRESSION_GUARD_TEST: PASS
VALIDATE_PR: GREEN
GATE_NOISE: <none | verbatim text>
```

**When BLOCKED — write `.ce/wt-ce501/BLOCKED` and stop immediately:**
```
STATUS: BLOCKED
BRANCH: ce-501-queue-canary
BLOCKER: <one-sentence description>
GATE: <BRAIN-LEDGER-BUSY | STOP-LINE | VALIDATE-PR-EXTERNAL | OTHER>
CONTEXT: <full context for controller resolution>
```

---

## UNIT U2 — ce-502-standby-surface

**Branch:** `ce-502-standby-surface`
**Worktree:** `~/creator-engine-ce-502-standby-surface` (off `origin/main`)
**Ticket:** ce-ops#502
**Work class:** S

### Worktree setup

```bash
git fetch origin
git worktree add ~/creator-engine-ce-502-standby-surface -b ce-502-standby-surface origin/main
cd ~/creator-engine-ce-502-standby-surface
```

---

### Full ticket body (ce-ops#502)

> **title:** Standby controller must reach `ce takeover` from a main-tracked surface, not the
> shared mutable checkout
>
> **labels:** bug, triage:ready, wc:S
>
> **Parent program:** ce-ops#471 (controller power-shaping + continuity), ce-ops#496
> (controller parity / IaC)
> **Related:** ce-ops#477 (takeover verb), ce-ops#488 (hydration contract)
> **Evidence:** D6 Drill #1, 2026-07-08 —
> `.ce/state/research/D6_DRILL1_REPORT_20260708.md`
>
> ## Symptom
>
> D6 Drill #1 (2026-07-08) mandated the codex standby controller (tmux `ce-controller` on
> DGX, `cedev2`) to emit a `ce takeover --dry-run --json` evidence packet. Result: **FAIL**.
> The standby's session runs from the shared root checkout `/home/cedev2/creator-engine`,
> which was parked on branch `ce-release-0.3.1-rc2`. On that branch `ce takeover` does not
> exist: `rc=2, "takeover is not a valid ce_cli command in this checkout"`. In a real outage
> this would have been the first act of succession — and it would have silently failed.
>
> ## Root cause
>
> The standby's `ce` reachability is coupled to whatever branch the shared checkout happens
> to be on. Release branches trail main; the takeover verb lives only on main (merged tonight
> via PR #877). There is no mechanism today that guarantees the standby can invoke
> `ce takeover` regardless of the shared checkout's state.
>
> ## Secondary finding
>
> During the drill window, `mint-forge-token.py` produced a traceback in the standby's
> environment — an import/runtime regression not present on the controller's main-tracked
> surface. Fold into the same provisioning fix.
>
> ## Impact
>
> - The primary failure scenario the weekly drill is designed to catch (Drill #1 ratified
>   under ce-ops#471, Decision 8) is itself blocked by a provisioning gap, not by the verb
>   or hydration logic.
> - The controller-parity chain (ce-ops#496) is end-to-end GREEN on `origin/main` (verified:
>   `b2a2c27c3`, ring0_verify.ok=true, all 6 hydration steps present) — the gap is purely the
>   standby's surface, not the harness.
>
> ## Fix direction
>
> 1. **Dedicated main-tracking surface for the standby**: provision the standby with its own
>    worktree pinned to `origin/main` (e.g. `/home/cedev2/ce-standby-main/`) OR use the
>    installed `ce` binary (which tracks releases, not branches). The standby MUST NOT launch
>    from the shared mutable checkout.
> 2. **Token-mint helper repair**: fix or replace `mint-forge-token.py` in the standby's
>    environment so it executes without traceback.
> 3. **Liveness check in weekly drill acceptance**: the drill is not GREEN until the standby
>    itself (not a separate main-tracked worktree) emits a `ce takeover --dry-run --json`
>    packet with `ring0_verify.ok=true`. Add this as an explicit acceptance gate in the drill
>    runbook (ce-ops#477 / weekly cadence from ce-ops#471 Decision 8).
>
> ## Acceptance criteria
>
> - The standby controller, launched from its own provisioned main-tracking surface, emits
>   `ce takeover --dry-run --json` → rc=0, `ring0_verify.ok=true`,
>   `initial_state=AWAITING-OPERATOR` **from the standby itself** (not from the primary
>   controller's worktree).
> - This passes in the next weekly drill run, replacing the D6 Drill #1 FAIL result.
> - `mint-forge-token.py` executes without error in the standby env.

---

### Scope — U2

Three fix slices, one branch, one PR.

**Slice A — Standby provisioning script**

New file: `deploy/dgx-controller-runsc/provision-standby-surface.sh`

This is a runnable bash script that provisions the DGX standby controller surface. It must:

1. Create (if absent) a dedicated main-tracking git worktree at `$STANDBY_ROOT`
   (default: `/home/cedev2/ce-standby-main`):
   ```bash
   git -C /home/cedev2/creator-engine fetch origin main
   if [[ ! -d "$STANDBY_ROOT/.git" ]]; then
     git -C /home/cedev2/creator-engine worktree add "$STANDBY_ROOT" origin/main
   else
     git -C "$STANDBY_ROOT" fetch origin
     git -C "$STANDBY_ROOT" checkout main
     git -C "$STANDBY_ROOT" reset --hard origin/main
   fi
   ```
2. Verify `ce takeover --dry-run --json` is reachable from the standby root:
   ```bash
   cd "$STANDBY_ROOT"
   ce takeover --dry-run --json | python3 -c "
   import json, sys
   r = json.load(sys.stdin)
   assert r.get('ring0_verify', {}).get('ok') is True, f'ring0_verify.ok not true: {r}'
   assert r.get('initial_state') == 'AWAITING-OPERATOR', f'wrong initial_state: {r}'
   print('OK: standby ce takeover --dry-run --json passed')
   "
   ```
3. Verify `mint-forge-token.py` executes without traceback from the standby root
   (call it as a dry-run/help invocation — `python3 tools/mint-forge-token.py --help`).
4. Emit a provisioning summary to stdout:
   ```
   STANDBY SURFACE PROVISIONED
   root: <STANDBY_ROOT>
   main sha: <git rev-parse HEAD in standby>
   takeover dry-run: OK
   mint-forge-token: OK
   ```
5. Exit 0 on success; exit 1 with a descriptive error on any failure.

The script must be idempotent (re-running it on an already-provisioned surface is safe).
Add a `--dry-run` flag that prints what it WOULD do without making changes.

**Slice B — mint-forge-token.py repair**

New file: `tools/mint-forge-token.py`

Create (or replace) a standalone Python helper script that mints a short-lived forge
(GitHub App) token for use by the standby controller. The script must:

- Accept `--help` without traceback.
- Accept `--dry-run` to print what it would do without contacting any service.
- When invoked for real: use `ce` CLI or environment credentials to produce a forge token
  for the standby's egress scope, or document clearly that full token minting requires
  the egress broker (and exit with a clear message rather than a traceback).
- The key fix: no import-time failures. The traceback from the D6 drill was a runtime
  import error. Ensure all imports are guarded and produce actionable error messages rather
  than raw tracebacks. Use `try/except ImportError` with `sys.exit(1)` + printed guidance
  if optional dependencies are unavailable.
- Include a `__main__` block.

Minimum viable `tools/mint-forge-token.py` that satisfies the AC:
```python
#!/usr/bin/env python3
"""Forge token minter for standby controller use.

Usage:
  mint-forge-token.py [--dry-run] [--help]

Requires: GH_TOKEN or CE egress broker configured.
"""
import argparse
import os
import sys

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done without minting")
    args = parser.parse_args()

    if args.dry_run:
        print("DRY-RUN: would mint a forge token via CE egress broker or GH_TOKEN env")
        print("DRY-RUN: GH_TOKEN present:", "yes" if os.environ.get("GH_TOKEN") else "no")
        return

    token = os.environ.get("GH_TOKEN")
    if not token:
        print(
            "ERROR: GH_TOKEN not set. "
            "Set GH_TOKEN or configure the CE egress broker for token minting.",
            file=sys.stderr,
        )
        sys.exit(1)

    # For now: emit the ambient GH_TOKEN as the forge token.
    # Production: replace with egress broker call (ce-ops#157 mint-broker).
    print(token)

if __name__ == "__main__":
    main()
```

This eliminates the import-time traceback while being honest about the current implementation
state. The docstring and error message document the path to full broker integration.

Add `tools/mint-forge-token.py` to `.gitignore` exception if tools/ is gitignored — check
first with `git check-ignore -v tools/mint-forge-token.py`.

**Slice C — Drill runbook update (continuity_drill_runtime.py)**

Modify `validators/creator_engine_validator/continuity_drill_runtime.py` to add a
`standby_liveness` check to the drill result schema.

Guidance:
1. Add a `standby_liveness` field to the `DrillRecord` or equivalent result type. The field
   records whether the standby itself emitted a valid `ce takeover --dry-run --json` packet
   with `ring0_verify.ok=true` during the drill window.
2. The drill runbook protocol (in `run_drill` or the acceptance-gate check) must emit a
   structured note if `standby_liveness` is absent or false: `"standby_liveness": "ABSENT —
   D6 Drill #1 gap; provision standby surface per ce-502"`.
3. The drill result is not `GREEN` (or equivalent passing status) unless `standby_liveness`
   is present and true. A missing standby_liveness field must degrade the result to a
   `WARNING` status (not outright failure, since the standby surface may not yet be
   provisioned on all hosts), but it must be visible in the drill JSON output.
4. Update the matching test in `validators/tests/unit/test_continuity_drill_cli.py`:
   - Add a test case that asserts `standby_liveness` appears in the drill result when
     the standby liveness context is provided.
   - Add a test case that asserts the drill degrades to `WARNING` (or equivalent) when
     `standby_liveness` is absent.

**Do NOT** add a new Python module in `validators/creator_engine_validator/`. Modify
`continuity_drill_runtime.py` in-place. No `_versions.py` change is needed (the module is
already registered as a V1_RUNTIME module).

---

### Stop line — U2

No pushes, no PRs, no edits outside these paths:

```
deploy/dgx-controller-runsc/provision-standby-surface.sh  (new)
tools/mint-forge-token.py  (new)
validators/creator_engine_validator/continuity_drill_runtime.py  (existing, modify)
validators/tests/unit/test_continuity_drill_cli.py  (existing, modify)
.ce/changelog/ce-502-standby-surface.md  (new)
.ce/pr-manifests/ce-502-standby-surface.md  (new)
.ce/wt-ce502/READY  (new)
.ce/wt-ce502/BLOCKED  (new)
```

Absolute stop-lines — do NOT touch:
- `.ce/brain/assertions.yaml` (PR #918 exclusive territory — BRAIN-LEDGER-BUSY blocker)
- `deploy/dgx-runsc/run-codex-runsc.sh` (PR #918)
- `deploy/vps-runsc/run-vps-runsc.sh` (PR #918)
- `validators/creator_engine_validator/ce_cli.py` (PR #918)
- `validators/creator_engine_validator/ce_onboard.py` (PR #918)
- `validators/creator_engine_validator/_versions.py` (no new module added in U2)
- `validators/tests/unit/test_ce_onboard.py` (PR #918)
- `validators/creator_engine_validator/forge/integrator_belt.py` (dev-4 in-flight)
- `validators/tests/unit/test_integrator_belt.py` (dev-4 in-flight)
- `deploy/daemons/smoke-daemon-container.sh` (dev-4 in-flight)
- `validators/tests/integration/test_adoption_merge_group_e2e.py` (dev-4 in-flight)
- `validators/tests/integration/test_release_finalize_integration.py` (dev-3 in-flight)
- `.github/scripts/ceops_autoclose.py` (dev-3 in-flight)
- `.github/workflows/ce-ops-autoclose.yml` (dev-3 in-flight)
- `validators/tests/unit/test_p2_acceptance_evidence.py` (dev-3 in-flight)

If `ce validate-pr` raises a gate on any file outside your diff, report it verbatim in the
READY signal under `GATE_NOISE` and do NOT touch the external file to silence it.

---

### Pre-authorization notes — U2

The following are pre-authorized; do NOT stop-line at them:

| Item | Status |
|------|--------|
| Modify `continuity_drill_runtime.py` to add `standby_liveness` field | IN SCOPE — Slice C |
| Modify `validators/tests/unit/test_continuity_drill_cli.py` for new gate | IN SCOPE — Slice C |
| Create `tools/mint-forge-token.py` with `--help`/`--dry-run` flags | IN SCOPE — Slice B |
| Create `deploy/dgx-controller-runsc/provision-standby-surface.sh` | IN SCOPE — Slice A |
| Drill result status degraded to WARNING when standby_liveness absent | IN SCOPE — Slice C |
| Idempotent re-provisioning behavior in provision-standby-surface.sh | IN SCOPE — Slice A |

**_versions.py:** `continuity_drill_runtime` is already in `V1_RUNTIME` in `_versions.py`.
No change to `_versions.py` is required. Do NOT add new entries.

**STOP on:** any gate that requires touching `.ce/brain/assertions.yaml`. Signal BLOCKED
with `GATE: BRAIN-LEDGER-BUSY`.

---

### Acceptance criteria — U2

U2 is complete when ALL of the following hold:

1. `deploy/dgx-controller-runsc/provision-standby-surface.sh` exists, is executable
   (`chmod +x`), runs with `--dry-run` without error, and the provisioning logic matches
   Slice A above.
2. `tools/mint-forge-token.py` exists, runs `python3 tools/mint-forge-token.py --help`
   without traceback, and `python3 tools/mint-forge-token.py --dry-run` exits 0 with
   descriptive output.
3. `validators/creator_engine_validator/continuity_drill_runtime.py` contains the
   `standby_liveness` gate (Slice C).
4. Affected tests in `validators/tests/unit/test_continuity_drill_cli.py` pass:
   ```bash
   pytest validators/tests/unit/test_continuity_drill_cli.py -v
   ```
5. Full `ce validate-pr` GREEN on the working tree.
6. Changelog fragment `.ce/changelog/ce-502-standby-surface.md` present.
7. Carrier `.ce/pr-manifests/ce-502-standby-surface.md` present with `slug: ce-502-standby-surface`,
   all changed paths listed, exactly one `- **Declared work class:** S` line, zero ce-ops#
   references.
8. PR opened (non-draft) on `ce-502-standby-surface`, PR body carries
   `- **Declared work class:** S`.
9. Signal file `.ce/wt-ce502/READY` written and committed as the FINAL commit.

---

### Standing obligations — U2

**Changelog** — `.ce/changelog/ce-502-standby-surface.md`:

```markdown
## ce-502-standby-surface

- fix(standby): provision dedicated main-tracking surface + mint-forge-token repair + drill gate

  Adds deploy/dgx-controller-runsc/provision-standby-surface.sh to provision the standby
  controller with its own main-tracking git worktree (default /home/cedev2/ce-standby-main),
  decoupling it from the shared mutable checkout. Fixes the D6 Drill #1 FAIL where the
  shared checkout on ce-release-0.3.1-rc2 lacked `ce takeover`.

  Adds tools/mint-forge-token.py replacing the traceback-producing helper with a
  guarded implementation that accepts --help and --dry-run without errors.

  Extends continuity_drill_runtime with a standby_liveness gate: drills missing a
  standby liveness proof degrade to WARNING status rather than silently passing.

  - **Declared work class:** S
```

**Carrier** — `.ce/pr-manifests/ce-502-standby-surface.md`:
- `slug: ce-502-standby-surface`
- List ALL changed paths
- Exactly one `- **Declared work class:** S` line
- Zero ce-ops# references

**Preflight:**
```bash
cd ~/creator-engine-ce-502-standby-surface
pytest validators/tests/unit/test_continuity_drill_cli.py -v
ce validate-pr
```

**PR body** must include:
1. `- **Declared work class:** S` (exactly once, verbatim)
2. Evidence that `provision-standby-surface.sh --dry-run` exits 0
3. Evidence that `python3 tools/mint-forge-token.py --help` exits 0 without traceback
4. Pytest result for `test_continuity_drill_cli.py`
5. `GATE_NOISE: <none or verbatim>` if validate-pr raised external gates

---

### READY / BLOCKED signals — U2

**When DONE — write `.ce/wt-ce502/READY` and commit as the final commit:**
```
STATUS: READY
BRANCH: ce-502-standby-surface
COMMIT: <HEAD SHA>
PR: <number>
PROVISION_DRY_RUN: OK
MINT_FORGE_TOKEN_HELP: OK
DRILL_STANDBY_GATE: PRESENT
CONTINUITY_DRILL_TESTS: PASS
VALIDATE_PR: GREEN
GATE_NOISE: <none | verbatim text>
```

**When BLOCKED — write `.ce/wt-ce502/BLOCKED` and stop immediately:**
```
STATUS: BLOCKED
BRANCH: ce-502-standby-surface
BLOCKER: <one-sentence description>
GATE: <BRAIN-LEDGER-BUSY | STOP-LINE | VALIDATE-PR-EXTERNAL | VERSIONS-REGISTRY | OTHER>
CONTEXT: <full context for controller resolution>
```

---

## EXECUTION ORDER

Complete U1 first (smaller, shell-only change; faster to validate). When U1 is pushed and PR
open, begin U2. Both worktrees may coexist concurrently on the host if resources permit, but
do not merge or interfere between branches.

---

## DROPPED UNITS (with reasons)

### ce-ops#500 — DROPPED: irresolvable territory conflict + partial prior landing

**Status at dispatch time:**
- PR #891 (`ce-500-launcher-durability`, MERGED 2026-07-07) already landed **slices (b) and (c)**
  of ce-ops#500 (durable worktree bind-mount and durable staging path out of /tmp).
- A post-merge comment on ce-ops#500 (2026-07-07 21:4xZ) added a **slice (d)**: preflight
  runners must set TMPDIR to a disk-backed path and cap pytest workers (not unlimited `-n auto`)
  on shared hosts.
- **Slice (a)** (per-seat cgroup memory ceiling in the contained launcher) and **slice (d)** remain open.

**Why dropped from this batch:**
- Slice (a) requires `deploy/vps-runsc/run-vps-runsc.sh` and `deploy/dgx-runsc/run-codex-runsc.sh`.
  Both files are in **PR #918 (ce-hermes-retirement) exclusive territory** (confirmed from PR #918
  file manifest). These paths cannot be targeted until #918 merges.
- Slice (d) scope is not fully specified (pytest runner config, Makefile, or test infra); needs
  further triage to identify exact files without overlap with in-flight work.

**Action required (controller):** After PR #918 merges, re-open ce-ops#500 targeting for the
next batch. Slice (a) cgroup cap and slice (d) TMPDIR/worker-cap are the remaining open items.

---

## IN-FLIGHT TERRITORY MAP (reference)

Paths excluded from this batch due to in-flight claims:

| Territory source | Claimed paths (representative) |
|-----------------|-------------------------------|
| PR #918 (ce-hermes-retirement, OPEN) | `.ce/brain/assertions.yaml`, `deploy/dgx-runsc/run-codex-runsc.sh`, `deploy/vps-runsc/run-vps-runsc.sh`, `validators/creator_engine_validator/ce_cli.py`, `validators/creator_engine_validator/ce_onboard.py`, `validators/tests/unit/test_dgx_runsc.py`, `validators/tests/unit/test_vps_runsc_launcher.py`, `.claude/hooks/ce-*`, `docs/delivery/NEXT_TASK_PROTOCOL.md`, `docs/delivery/WORKTREE_RUNTIME_PROTOCOL.md`, + 17 others |
| dev-4 in-flight | `validators/creator_engine_validator/forge/integrator_belt.py`, `validators/tests/unit/test_integrator_belt.py`, `deploy/daemons/smoke-daemon-container.sh`, `validators/tests/integration/test_adoption_merge_group_e2e.py` |
| dev-3 in-flight | `validators/tests/integration/test_release_finalize_integration.py`, `.github/scripts/ceops_autoclose.py`, `.github/workflows/ce-ops-autoclose.yml`, `validators/tests/unit/test_p2_acceptance_evidence.py` |

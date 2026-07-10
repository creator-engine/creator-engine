# D6 DRILL #1 REPORT — 2026-07-08 (night-arc set-piece, COMPLETE — failed usefully)

## Design
No-gate-authority drill: the codex standby (tmux ce-controller, verified alive/authed)
was mandated to produce a `ce takeover --dry-run --json` evidence packet. No hydration
execution, no gate acts — pure evidence emission, per the ratified drill bounds.

## Result 1 — STANDBY ENVIRONMENT: FAIL (the drill's real finding)
The standby's session runs from the root checkout parked on branch
ce-release-0.3.1-rc2 — where `ce takeover` DOES NOT EXIST. rc=2,
"takeover is not a valid ce_cli command in this checkout". In a real outage the
standby's first act would have failed exactly here. Root cause class: the standby's
harness reachability depends on its checkout's branch — takeover must be reachable
from an installed/main-tracked surface, not whatever branch the shared checkout
happens to be on. (Same lesson family as controller-parity #496: environment must be
provisioned, not inherited.) TICKETED.

## Result 2 — HARNESS ON MAIN: GREEN (controller-side verification)
From a fresh origin/main worktree (b2a2c27c3), `ce takeover --from
claude-main-controller --harness codex --repo-root /home/cedev2/creator-engine
--dry-run --json` → rc=0, kind=ce-takeover-evidence-packet, initial_state=
AWAITING-OPERATOR, ring0_verify.ok=true, raw_controller_launch_refusal=
READ_ONLY_UNTIL_GOVERNED_LAUNCH_CONFIRMED, hydration_plan (ALL execute=false):
detect-predecessor-state → hydrate-brain-memory → verify-ring0-harness →
hydrate-continuity-packet → read-forge-housekeeping-runbook → enter-awaiting-operator.
Both actions shipped TONIGHT (#888 brain hydration, #883 runbook read) are present in
correct order — the controller-parity chain reaches the takeover surface end-to-end.

## Secondary observation
The standby's stderr showed a mint-forge-token.py traceback during the drill window —
its token-mint helper has an import/runtime issue in that env; fold into the
standby-provisioning fix.

## Drill disposition
Drill #1 = COMPLETE. A drill that finds the standby cannot start is a SUCCESSFUL
drill. Next drill (weekly cadence per ratified program) re-runs after the standby
checkout fix; acceptance = the STANDBY emits the green packet itself.

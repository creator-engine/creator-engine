# A2 double-drive sequencing — Option A RATIFIED (Operator, 2026-07-04 ~17:55Z, in-session form-echo)
> Prepared by CE-DEV-2, 2026-07-04 ~17:50Z. Resolves canary/live precondition 3 in
> A2_BELT_SHADOW_STAGING_20260704.md. Ratified decision text = "Decision text for ratification"
> section below, selected verbatim via option "Ratify Option A (Recommended)".

## Problem
Two independent processes must never simultaneously hold live merge-gate authority
(queue-daemon: mint capability markers, enqueue `gh pr merge --auto`). Today the DGX host-venv
wall daemon owns it. A2's dev-1 belt is in shadow; flipping it live as-is would create a second
armed driver. The mandate's containerized-first refinement requires the flip to land on the
container form regardless.

## Evidence (code-verified 2026-07-04)
1. **No mutual exclusion exists.** queue-daemon has no lease/singleton seam (the DaemonLease
   pattern is conveyor-only, landed with A1). Singleton today = launch-script convention +
   controller pgrep checks.
2. **Marker minting is an unguarded read-modify-write** of the PR body
   (integrator_belt.py:_upsert_approval_capability_marker → _update_pr_body). Two live daemons
   interleaving = lost-update races: a freshly minted marker can be clobbered or a stripped stale
   marker resurrected. The ce-ops#404 stale-marker → head_mismatch deadlock shows this seam
   fails silently when markers desync.
3. **Settle windows are per-instance local state** (state.json). Two daemons keep independent
   approval-settle clocks → duplicate enqueue attempts and inconsistent settle enforcement.
4. Shadow evidence: dev-1 dry-run decisions independently MATCHED the live daemon's timeline —
   both compute identical decisions, so redundancy adds noise/races, not correctness.
5. review-pickup is a DIFFERENT authority class: routing/review-requests + inbox writes only, no
   merge authority; shadow showed native dedupe (requested=false when already requested).

## Options
**A — Single-owner with replacement cutover (RECOMMENDED, default).**
Merge-gate authority is a SINGLETON by policy. The containerized queue-daemon REPLACES the DGX
host daemon on the same host via stop-old → start-new cutover (never both armed; the OpenBao
secret custody surface stays one host). Kill-switch = stop container, re-run
~/ce-wall-daemon-launch.sh (kept intact until soak complete, ≥3 arc-days green).
review-pickup goes live separately on dev-1's containerized form once its OpenBao identity
wiring (precondition 2) lands — its authority class permits this without the singleton cutover.
Moving queue-daemon ownership DGX→dev-1 later is a separate, deliberate cutover under the same
single-owner rule.
- Cost: brief gate downtime at cutover (bounded by one daemon interval, 120s); no new code.
- Residual: singleton remains convention-until-coded → fast-follow ticket: extend the A1
  DaemonLease seam to queue-daemon so a second armed instance refuses at startup (fail-closed,
  same pattern the conveyor already has).

**B — Active-active with distributed lease.** Requires a cross-host lock (forge-based or shared
store) that doesn't exist; new engineering + new failure modes to serialize work one daemon
already handles at current scale. Rejected as premature.

**C — Active-passive warm standby.** Second instance armed-but-held behind a standby flag with a
manual promotion runbook. No races, but adds a promotion procedure and a second live secret
custody surface for availability we don't currently need (gate downtime is self-healing via
restart). Viable later as an HA upgrade on top of A; not the flip vehicle.

## Decision text for ratification (form-echo)
"RATIFY A2-SEQ Option A: live merge-gate authority (queue-daemon with approval-wall) is a policy
singleton. The containerized queue-daemon replaces the DGX host daemon via stop-old→start-new
cutover with the host launcher retained as kill-switch until ≥3 arc-days green soak.
review-pickup may go live on dev-1's containerized form independently once OpenBao identity
wiring lands. A fail-closed startup lease for queue-daemon is commissioned as a fast-follow.
Any later ownership move to another host is a separate cutover under the same singleton rule."

## On ratification (controller executes, no further asks)
1. File the queue-daemon startup-lease fast-follow in ce-ops (references this memo + #443 pattern).
2. Stage the containerized cutover runbook (stop host daemon → launch via
   deploy/daemons/run-daemon-container.sh queue-daemon → verify daemon_pass in logs → 2-pass watch);
   execute per the deployment-flip gates already in the mandate.
3. Sequence review-pickup containerized go-live behind precondition 2 (OpenBao wiring), not behind
   the queue-daemon cutover.

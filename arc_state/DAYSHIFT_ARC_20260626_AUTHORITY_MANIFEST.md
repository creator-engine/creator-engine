# 🏭 AUTONOMOUS AUTHORITY MANIFEST — Day-shift arc 2026-06-26 (dark-factory)
Purpose: batch-ratify the bounded gates so the arc runs without Operator-as-bottleneck. Operator remains available for unforeseen events. Grounded in [[ce-autonomous-authority-doctrine]] (bar = consequence × novelty × irreversibility; GRANTED ≠ exercised) + [[batch-strict-mode-gate-workflow]].

## GRANTS REQUESTED (each bounded; stop-conditions auto-halt)
**G1 — Conveyor merge authority (arc units).** Controller reviews-as-ce-dev-2, approves, enqueues PRs through the armed approval-capability wall (wall + auto-merge lands them). BOUNDS: only if full host BASELINE-DIFF clean (zero NEW failures vs origin/main; DGX has ~64 pre-existing) + `--require-carrier` PASS + within arc scope + work-class declared. NOT: merging red, force-merge bypassing the wall, out-of-arc large diffs. (Already exercised overnight; this formalizes it.)

**G2 — Queue/dispatch + seat lifecycle.** Stock queue, dispatch born-a-foreman units, harvest, re-stock, /compact (>40% ctx) or /clear (wave boundary) seats, spawn worker-forks — within arc scope. BOUNDS: stay within the ratified arc ticket-set + close residuals; surface NEW out-of-arc scope before starting.

**G3 — #249 split execution (already "go"-ed).** Merge ce-ops backup of the verified 22, then push+merge the public delete+scrub PR (exactly the 22-relocate / 8-scrub set) via review+wall, no separate diff review. BOUNDS: exactly the verified set; backup-merged-first; baseline-diff + #476 dangling-link guard green.

**G4 — OpenBao wall routine ops.** Renew the daemon's 72h token before expiry (~Jun 28 15:42); keep wall armed; daemon health. NOT: change wall policy/secret, re-key, disarm.

**G5 — GATE β autonomy CANARY (highest-consequence; bounded pre-auth requested).** Once #219 (Ring-1) lands AND I verify HARD per-tool-call deny on a contained seat (restricted mechanic w/o envelope → DENIED, documented proof), enable self-push + self-review on ONE canary seat (dev-3) for ONE real arc PR end-to-end behind wall + Ring-1. BOUNDS/AUTO-ABORT: #219 verified-hard first; one seat / one PR; ABORT+report if the seat acts outside its envelope, if Ring-1 fails any deny-probe, or if the self-pushed PR isn't wall-gated; do NOT extend fleet-wide until I report the canary result to you.

## RESERVED — stays Operator-gated (recommend keep)
- R1 Fleet-wide autonomy rollout (after a clean canary report).
- R2 External-facing release / publish / real-user (Arad) onboarding — anything a real external person touches.
- R3 Git-history scrub (already NOT authorized).
- R4 Granting any seat authority BEYOND its envelope, or weakening/disabling a governance guard.
- R5 Irreversible destructive ops outside ratified sets (force-push to main, repo settings, secret re-key, deleting non-classified content).
- R6 New high-consequence scope outside the arc's 4 programs.

## STANDING STOP-CONDITIONS (auto-halt → ⏸️ AWAITING-OPERATOR)
Bad merge/regression reaching main · any Ring-1/wall/containment guard failing to deny what it should · any credential surfacing in env/argv/transcript · two-strikes on any gate · anything matching RESERVED.

## STATUS: ✅ RATIFIED 2026-06-26 (Operator: "ratify all incl. G5 canary"). G1-G5 GRANTED with bounds; R1-R6 reserved. Arc runs autonomously; Operator available for unforeseen events.

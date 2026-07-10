# D3 SHADOW-CANARY REPORT — 2026-07-08 (night-arc set-piece, COMPLETE)

## What ran
A second, zero-authority instance of the merge-gate queue daemon (`ce-queue-canary`,
same image creator-engine/ce-runtime:0.3.2-main) observed the live repo in dry-run
for a ~45-minute window while the armed daemon (`ce-queue-daemon`) processed real
merges (#889/#892/#893 landed during the window).

## Zero-authority construction (proven, not asserted)
- `--dry-run`: enqueue path logs `eligible_dry_run`, never reaches `gh pr merge`.
- Approval wall DORMANT: launched by DIRECT daemon invocation with NO
  `--approval-wall-secret-*` flags (no backend supplier → `secret_not_configured`
  → dormant → marker issuer None). The stock launcher CANNOT do this: it hardwires
  `--approval-wall-secret-backend openbao`, which converts dormancy into a
  `configured_backend_without_secret` refusal (fail-closed — correct for the live
  gate, blocking for canaries). GAP TICKETED.
- Forge credential: GitHub App installation token downscoped at mint to
  contents:read + pull_requests:read (+implicit metadata:read); `push: False`
  verified pre-launch; 1-hour expiry bounded the canary's life; token shredded after.
- Isolated state root (/home/cedev2/ce-canary-state, own lease dir — no collision
  with the live daemon's singleton lease); worktree shared READ-ONLY.

## Parity result: GREEN — no decision-logic divergence
Every comparable (status, reason) decision class matched across the window
(defer/approval_settle_pending, enqueue/eligible*, skip/governance_check_not_success,
skip/review_not_approved on PRs #889/#893). Three deltas, all design-explained:
1. Pass-timing set differences (live saw CI-pending passes the canary's offset
   schedule missed, and #892's decisions predate canary start) — windowing, not logic.
2. Canary never emits defer/approval_capability_minted — DORMANT wall cannot mint;
   this is the intended authority asymmetry.
3. Dry-run reaches terminal eligibility WITHOUT a minted marker — dry_run
   short-circuits the marker requirement. Semantic note: canary parity on the final
   eligibility step is therefore approximate BY DESIGN; everything upstream of the
   marker step is exact.

## Follow-up (ticketed)
Launcher needs a first-class canary/dormant mode: an env flag (e.g.
CE_QUEUE_DAEMON_CANARY=1) that omits the secret-backend flags and relaxes
validate_required_env's BAO requirements, so a canary never needs the direct-invocation
workaround and never carries even placeholder BAO env.

Evidence: scratchpad canary_decisions.jsonl / live_decisions.jsonl (session-mortal);
decision histograms reproduced above. Canary container removed; state dir
/home/cedev2/ce-canary-state retained for inspection.

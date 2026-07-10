# WORK CLAIMS — day-arc-2 intake batch — 2026-07-08 (controller CE-DEV-2)

Territory-checked against open PRs (0), .ce/briefs/, .ce/claims/, git worktree list — no collisions.

## Claim 1 — dev-4 — ce-482-broker-v1-slice1
- Ticket: ce-ops#482 (host-ops broker v1, design merged #884)
- Brief: .ce/briefs/BRIEF_dev4_482_broker_slice1_20260708.md
- Paths: tools/host-ops-broker/**, validators/tests/unit/test_host_ops_broker_*.py, .ce/changelog+pr-manifests/ce-482-broker-v1-slice1.md
- Mode: commit-for-harvest (dev-4 commit-only)

## Claim 2 — dev-3 — ce-499-seat-ready-profile
- Ticket: ce-ops#499 (seat-side preflight, design merged #892)
- Brief: .ce/briefs/BRIEF_dev3_499_seat_ready_20260708.md
- Paths: validators/creator_engine_validator/pr_preflight.py, validators/tests/unit/test_pr_preflight.py, validators/tests/unit/test_ce_validate_pr_cli.py, .ce/changelog+pr-manifests/ce-499-seat-ready-profile.md
- Mode: commit-for-harvest (self-push canary not re-proven)

## Claim 3 — dev-1 — ce-iac-singleton-redeploy
- Authority: Operator decision 1, DECISIONS_20260708.md
- Brief: .ce/briefs/BRIEF_dev1_iac_ring1_20260708.md (U1)
- Paths: deploy/singleton-redeploy/**, docs/operations/SINGLETON_DAEMON_REDEPLOY_RUNBOOK.md, .ce/changelog+pr-manifests/ce-iac-singleton-redeploy.md
- Mode: self-push + PR

## Claim 4 — dev-1 — ce-ring1-launch-provenance
- Authority: Operator decision 4a, DECISIONS_20260708.md
- Brief: .ce/briefs/BRIEF_dev1_iac_ring1_20260708.md (U2)
- Paths: validators/creator_engine_validator/harness_matrix.py, validators/tests/unit/test_harness_matrix.py, docs/operations/HARNESS_SUPPORT_CAPABILITY_MATRIX.md, .ce/changelog+pr-manifests/ce-ring1-launch-provenance.md
- Mode: self-push + PR

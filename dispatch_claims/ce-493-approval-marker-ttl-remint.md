# WORK CLAIM — ce-493-approval-marker-ttl-remint
claimed: 2026-07-09T06:4xZ (fleet restock batch dev-4; ce-ops#493)
seat: dev-4 (ce-dgx-codex, contained commit-only)
branch: ce-493-approval-marker-ttl-remint
paths: validators/creator_engine_validator/forge/integrator_belt.py (modify: add expired-reason re-mint path + expired_review_valid/absent reason values) + validators/tests/unit/test_integrator_belt.py (extend: two new test cases) + changelog + carrier
brief: .ce/briefs/BRIEF_dev4_restock_batch_20260709.md
constraints: GATE-ADJACENT — no change to non-expired paths; ARMING_ENABLED unchanged; no brain assertions.yaml touch; fail-closed re-mint only; COMMIT-ONLY; commit early and often (runsc RAM)

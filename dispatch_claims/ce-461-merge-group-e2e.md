# WORK CLAIM — ce-461-merge-group-e2e
claimed: 2026-07-09T06:4xZ (fleet restock batch dev-4; ce-ops#461 — prior stale claim ce-461-adoption-e2e-fixture abandoned 2026-07-06; prerequisite ce-ops#473 now resolved via PR #859)
seat: dev-4 (ce-dgx-codex, contained commit-only)
branch: ce-461-merge-group-e2e
paths: validators/tests/integration/test_adoption_merge_group_e2e.py (new: adoption e2e against non-CE-shaped fixture; asserts merge_group parity with CE's own validate.yml) + changelog + carrier
brief: .ce/briefs/BRIEF_dev4_restock_batch_20260709.md
constraints: test-only unit; no production module changes; no onboard_apply.py touch; no brain assertions.yaml touch; pytestmark=slow required; COMMIT-ONLY

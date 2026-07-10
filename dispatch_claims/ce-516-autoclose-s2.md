# WORK CLAIM — ce-516-autoclose-s2
claimed: 2026-07-09T06:4xZ (fleet restock batch dev-3; ce-ops#516)
seat: dev-3 (ce-vps-codex, contained commit-only)
branch: ce-516-autoclose-s2
paths: .github/scripts/ceops_autoclose.py (modify: dedup guard + alerting hook) + .github/workflows/ce-ops-autoclose.yml (modify: comment refresh only) + validators/tests/unit/test_p2_acceptance_evidence.py (extend: POST-failure test) + changelog + carrier
brief: .ce/briefs/BRIEF_dev3_restock_batch_20260709.md
constraints: no brain assertions.yaml touch; no test_ceops_autoclose.py touch; no logic change to existing close path; COMMIT-ONLY

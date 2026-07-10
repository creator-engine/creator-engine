# WORK CLAIM — ce-427-approver-ref-provenance
claimed: 2026-07-09T00:00Z (dev-3 batch 3, restock3) — supersedes stale dev-1 claim 2026-07-05 (no PR ever opened; work never started)
seat: dev-3
ticket: ce-ops#427 [G12] client-side approver_ref provenance (parent design ce-ops#421 §6.1)
branch: ce-427-approver-ref-provenance
paths:
  - validators/creator_engine_validator/schemas/install-answers.schema.yaml (add optional approver_ref_provenance to ratification_binding $def)
  - validators/creator_engine_validator/approver_ref_minting.py (NEW — mint_approver_ref + verify_approver_ref)
  - validators/tests/unit/test_approver_ref_minting.py (NEW)
  - .ce/changelog/ce-427-approver-ref-provenance.md
  - .ce/pr-manifests/ce-427-approver-ref-provenance.md
brief: /home/cedev2/creator-engine/.ce/briefs/BRIEF_dev3_restock3_20260709.md

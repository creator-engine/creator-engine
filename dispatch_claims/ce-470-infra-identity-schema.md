# WORK CLAIM — ce-470-infra-identity-schema
claimed: 2026-07-09T00:00Z (dev-1 batch 2, restock2)
seat: dev-1
ticket: ce-ops#470 Infra-identity SSOT auto-recall (S-slice 1: schema + example + precedence rule)
branch: ce-470-infra-identity-schema
paths:
  - validators/creator_engine_validator/schemas/identity-registry.schema.yaml (extend app $def)
  - docs/governance/identity-registry.example.yaml (add mythos-ce template + precedence rule)
  - validators/tests/unit/test_identity_registry_schema.py (extend with tenant-App tests)
  - .ce/changelog/ce-470-infra-identity-schema.md
  - .ce/pr-manifests/ce-470-infra-identity-schema.md
brief: /home/cedev2/creator-engine/.ce/briefs/BRIEF_dev1_restock2_20260709.md (Unit B)
note: slice 1 of 2; sub-problem (b) recall path (ce identity lookup CLI) deferred to post-PR-918

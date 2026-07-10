# WORK CLAIM — dev-3 batch (3 units)
claimed: 2026-07-08T18:4xZ (dispatching now; STRANGELOOP-1 P0 in-flight set)
seat: dev-3 (self-push, non-draft PRs)
brief: .ce/briefs/BRIEF_dev3_batch_docs_preflight_20260708.md (sha256 3b2d04090a56c9b444846024f97f7a570e331c70f8cb5d131e0f2360e59f10a7)
units:
  - branch ce-solo-ceo-onboarding-fix (ce-ops#514): docs/guide/solo-ceo-onboarding.md
  - branch ce-seat-preflight-parity: validators/creator_engine_validator/pr_preflight.py (seat-ready
    profile portability skip) + validators/tests/unit/test_pr_preflight.py
  - branch ce-readme-review-minors (PRECONDITION: after ce-readme-overhaul merges):
    checks/version_drift.py + test_version_drift.py + docs/reference/cli.md + ce_cli.py
    PRE_ARGPARSE_DISPATCH_GROUPS + test_v1_docs_reconciliation.py
known-overlap: test_pr_preflight.py also appended by dev-4 ce-491-prearming — dev-3 brief mandates
rebase-check vs origin/ce-491-prearming before push.
constraints: NO .ce/brain/assertions.yaml edits anywhere (ledger tail reserved for dev-1 hermes R2).

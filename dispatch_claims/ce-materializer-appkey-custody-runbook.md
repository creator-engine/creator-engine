# WORK CLAIM — ce-materializer-appkey-custody-runbook
claimed: 2026-07-10T13:4xZ
controller: ce-dev-2 (Claude face)
seat: dev-3 (ce-vps-codex) — queued behind ce-523c (foreman self-managed)
ticket: materializer pre-arming slice (c) (#471 program; unblocked by ADR-0015 merge efd82b03)
branch: ce-materializer-appkey-custody-runbook
role: implementer
work_class: S
scope: author docs/operations/MATERIALIZER_APPKEY_CUSTODY_RUNBOOK.md (App private-key custody
  lifecycle bound to ADR-0015 Q2 vault-signer per-call-fetch + Q4 MaterializerLease topology;
  authority matrix by ROLE; non-authorities; HELD failure/recovery) + register in the
  operations debt ratchet frozenset.
territory: docs/operations/MATERIALIZER_APPKEY_CUSTODY_RUNBOOK.md (NEW),
  validators/creator_engine_validator/public_docs_confidentiality.py (ratchet entry line only),
  changelog+carrier (NEW).
  Collision scan 2026-07-10T13:4x: NO COLLISIONS — no held-queue or open branch touches
  public_docs_confidentiality.py or docs/operations/MATERIALIZER* (scanned all 9 in-flight
  branches).
evidence_expected: READY-FOR-HARVEST ce-materializer-appkey-custody-runbook <40-hex-sha> after
  focused confidentiality test green.

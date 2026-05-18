# Governance Contract Documents

This directory contains the human-readable contract documents shipped by the Creator Engine v0.1 governance substrate.

Planned contract set and source FR coverage:

- `identity-record.md` — FR-001..FR-005.
- `spec-wrapper-sidecar.md` — FR-009, FR-010, FR-011, FR-012, FR-012a, FR-013a.
- `plan-wrapper-sidecar.md` — FR-012a, FR-012b.
- `tasks-wrapper-sidecar.md` — FR-012a, FR-012b, FR-007.
- `definition-of-ready.md` — FR-013.
- `mutation-class-taxonomy.md` — FR-006, FR-007, FR-008.
- `authority-matrix.md` — FR-015, FR-016.
- `ratification-flow.md` — FR-016, FR-017, FR-018.
- `lifecycle-state-machine.md` — FR-013a.
- `definition-of-done.md` — FR-014.
- `attestation-record.md` — FR-004, FR-005, FR-020a.
- `ratification-record.md` — FR-007, FR-016, FR-020a.
- `redaction-gate-policy.md` — FR-019, FR-020, FR-021.
- `redaction-record.md` — FR-020, FR-020a, FR-021.
- `validator-cli.md` — FR-025, FR-026, FR-027, FR-027a.
- `verification-spec/` and `verification-spec.md` — FR-030, FR-031.

The authoritative source for generated work remains the feature plan until each contract document is authored in its story phase.

CFC follow-on Batch 2D contract documents (post-Sprint-0 substrate; each lifts or extends a separate evidence artifact class and is governed under its own separately Source-ratified privileged `schema`-class envelope per Feature 001 FR-008):

- `review-evidence.md` — FR-001, FR-027 (Batch 2D.1 schema-class lift of `../delivery/REVIEW_EVIDENCE_TEMPLATE.md`; landed).
- `architect-evidence.md` — FR-001, FR-027 (Batch 2D.2 schema-class authoring; landed; sibling to review-evidence; does not amend review-evidence semantics and does not authorize implementer-class authoring).
- `implementer-evidence.md` — FR-001, FR-027 (Batch 2D.3 schema-class authoring; landed; sibling to review-evidence and architect-evidence; does not amend their semantics and does not authorize ratification, merge, deploy, branch deletion, branch protection mutation, live repository-settings change, provider/tool/model/host/account binding, tenant binding, or authority expansion).

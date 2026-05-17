# Contracts: Creator Engine v0.1 Governance Substrate

**Phase**: 1 (Design & Contracts) | **Date**: 2026-05-09

This directory enumerates the contracts the v0.1 governance substrate
*exposes*. Each contract document below names the artifact, the FRs it
satisfies, the surface (file shape / CLI surface / YAML schema location
the implementation will create), and the validator checks that enforce
it. These contracts are the basis for `/speckit-tasks` generation; the
files they describe are NOT created by `/speckit-plan`.

| Contract                                      | Implementation surface                                     | FRs |
|-----------------------------------------------|------------------------------------------------------------|-----|
| [identity-record](./identity-record.contract.md) | `docs/contracts/identity-record.md`, `schemas/identity-record.schema.yaml`, `templates/identity-record.template.yaml` | FR-001..FR-005 |
| [spec-wrapper-sidecar](./spec-wrapper-sidecar.contract.md) | `docs/contracts/spec-wrapper-sidecar.md`, `schemas/spec-wrapper-sidecar.schema.yaml`, `templates/spec.creator-engine.template.yaml` | FR-009, FR-010, FR-011, FR-012, FR-012a |
| [plan-wrapper-sidecar](./plan-wrapper-sidecar.contract.md) | `docs/contracts/plan-wrapper-sidecar.md`, `schemas/plan-wrapper-sidecar.schema.yaml`, `templates/plan.creator-engine.template.yaml` | FR-012a, FR-012b |
| [tasks-wrapper-sidecar](./tasks-wrapper-sidecar.contract.md) | `docs/contracts/tasks-wrapper-sidecar.md`, `schemas/tasks-wrapper-sidecar.schema.yaml`, `templates/tasks.creator-engine.template.yaml` | FR-012a, FR-012b |
| [mutation-class-taxonomy](./mutation-class-taxonomy.contract.md) | `docs/contracts/mutation-class-taxonomy.md`, `schemas/mutation-class.schema.yaml` | FR-006, FR-007, FR-008 |
| [authority-matrix](./authority-matrix.contract.md) | `docs/contracts/authority-matrix.md`, `schemas/authority-matrix.schema.yaml` | FR-015 |
| [ratification-flow](./ratification-flow.contract.md) | `docs/contracts/ratification-flow.md` | FR-016, FR-017, FR-018 |
| [attestation-record](./attestation-record.contract.md) | `docs/contracts/attestation-record.md`, `schemas/attestation-record.schema.yaml`, `templates/attestation-record.template.yaml` | FR-004, FR-005, FR-014, FR-020a |
| [ratification-record](./ratification-record.contract.md) | `docs/contracts/ratification-record.md`, `schemas/ratification-record.schema.yaml`, `templates/ratification-record.template.yaml` | FR-016, FR-017, FR-018, FR-020a |
| [redaction-gate-policy](./redaction-gate-policy.contract.md) | `docs/contracts/redaction-gate-policy.md` | FR-019, FR-020, FR-021 |
| [redaction-record](./redaction-record.contract.md) | `docs/contracts/redaction-record.md`, `schemas/redaction-record.schema.yaml`, `templates/redaction-record.template.yaml` | FR-020, FR-020a, FR-021 |
| [lifecycle-state-machine](./lifecycle-state-machine.contract.md) | `docs/contracts/lifecycle-state-machine.md`, `docs/contracts/definition-of-ready.md`, `docs/contracts/definition-of-done.md` | FR-013, FR-013a, FR-014 |
| [validator-cli](./validator-cli.contract.md) | `validators/creator_engine_validator/` (CLI surface, exit codes, output formats) | FR-025, FR-026, FR-027, FR-027a |
| review-evidence (Batch 2D.1 lift of [`../../../docs/delivery/REVIEW_EVIDENCE_TEMPLATE.md`](../../../docs/delivery/REVIEW_EVIDENCE_TEMPLATE.md)) | `docs/contracts/review-evidence.md`, `schemas/review-evidence.schema.yaml`, `templates/review-evidence.template.yaml` | FR-001, FR-027 (Batch 2D.1 schema-class lift; Batch 2D.2 architect-evidence and Batch 2D.3 implementer-evidence schemas remain downstream) |
| architect-evidence (Batch 2D.2 schema-class authoring) | `docs/contracts/architect-evidence.md`, `schemas/architect-evidence.schema.yaml`, `templates/architect-evidence.template.yaml` | FR-001, FR-027 (Batch 2D.2 schema-class authoring; sibling Batch 2D.1 review-evidence schema landed; Batch 2D.3 implementer-evidence schema remains downstream) |

## Contract authoring rules

- Every contract document under `docs/contracts/` is itself a
  Creator-Engine-governed artifact under
  `docs/contracts/verification-spec.md` (FR-031). Changes to a
  contract MUST follow the spec/plan/tasks lifecycle.
- No contract document under `docs/contracts/`, `schemas/`,
  `validators/`, or `templates/` may contain LIMITLESS-specific
  identifiers (FR-024, FR-024a, SC-004); LIMITLESS values appear only
  under `tenants/limitless/`.
- Where a contract has a corresponding YAML schema, the schema is the
  machine-checkable form and the prose is the human-readable form.
  When they disagree, the prose contract is treated as the authority
  for human review and the schema MUST be revised to match (with the
  revision itself going through the lifecycle).

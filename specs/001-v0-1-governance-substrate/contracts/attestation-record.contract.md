# Contract: Attestation Record

**Source FRs**: FR-004, FR-005, FR-014, FR-020a

## Purpose

Durable repo-native record that binds a mutation to its spec, agent
identity, mutation class, permitted-action list, verification
evidence, and ratifier identity. Carries a state discriminator so a
single record covers both the pre-merge mergeability proof and the
post-merge finalization with merge reference (research Decision 13).

## Implementation surface

- `docs/contracts/attestation-record.md` — human-readable contract,
  including the pre_merge / finalized state semantics.
- `schemas/attestation-record.schema.yaml` — JSON Schema enforcing
  state-conditional fields (e.g. `merge_reference` required when
  `state == finalized`).
- `templates/attestation-record.template.yaml` — project-agnostic
  template.

## File location and naming (FR-020a)

Under the tenant's `attestation_storage_path`. Filename
`<YYYY-MM-DD>-<mutation_id>.yml`. One record per mutation. No
append-only logs, no Markdown bodies.

## Required fields

`mutation_id`, `state` (`pre_merge` | `finalized`), `spec_ref`,
`agent_identity_ref`, `mutation_class`, `permitted_actions`,
`verification_evidence` (with `method` and `evidence_refs[]`, matching
the shared Verification Evidence shape), `ratifier_identity_ref`,
`created_at`. Conditional: `merge_reference` (required when `state
== finalized`).

## Validator checks

- `attestation_linkage.py`:
  - For status `verified`, a `pre_merge` attestation exists.
  - For status `done`, a `finalized` attestation exists with
    `merge_reference` populated.
  - `ratifier_identity_ref` ≠ author identity (FR-007).
  - `mutation_class` matches the spec's declared class.
- `definition_of_done.py`: rejects a self-claim where the
  `verification_evidence.evidence_refs` array is empty or authored only
  by the same agent identity (FR-014).

## Acceptance evidence

- Spec User Story 4, Acceptance Scenarios 1–4.
- SC-008: 0 governed mutations may merge without an attestation
  record naming spec, identity, mutation class, permitted actions,
  evidence, and ratifier.

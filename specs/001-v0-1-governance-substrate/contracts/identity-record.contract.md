# Contract: Tenant Identity Record

**Source FRs**: FR-001, FR-002, FR-003, FR-005

## Purpose

Names a tenant identity that is allowed to author Creator-Engine-governed
mutations. Joins agents to authority. Provides the storage paths for all
attestation, ratification, and redaction records the tenant produces.

## Implementation surface

- `docs/contracts/identity-record.md` — human-readable contract with
  field descriptions, examples (LIMITLESS-free), and the
  platform-vs-tenant identity distinction (FR-002).
- `schemas/identity-record.schema.yaml` — JSON Schema (Draft 2020-12)
  encoding the field shape from data-model.md Entity 1.
- `templates/identity-record.template.yaml` — project-agnostic
  template tenants copy when onboarding.

## Required fields (canonical list)

`tenant_id`, `source_host`, `source_host_installation_id`,
`agent_app_slug`, `agent_actor_id`, `runtime_tool`, `role_category`,
`authority_context`, `human_ratifier_roles` (non-empty),
`mutation_classes`, `allowed_repositories`, `signing_policy`,
`attestation_storage_path`, `ratification_storage_path`,
`redaction_storage_path`. Optional: `platform_identity_ref` for
distinguishing platform identity from tenant identity (FR-002).

## Validator checks (FR-027a-relevant)

- `identity.py`: required-field presence, `human_ratifier_roles`
  non-empty, every `mutation_classes` entry resolves, every storage
  path exists in the repo (or is permitted-empty for a not-yet-used
  tenant).
- `mutation_class.py`: `mutation_classes` references baseline or
  declared tenant-extension classes only.
- `no_limitless_strings.py`: this file does NOT contain any LIMITLESS
  identifier (when located outside `tenants/limitless/`).

## Acceptance evidence

- Spec User Story 1, Acceptance Scenarios 1–3.
- A reviewer can read one identity record and answer who, where, and
  what mutation classes are allowed (SC-001).

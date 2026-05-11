# Contract: Tenant Identity Record

Source FRs: FR-001, FR-002, FR-003, FR-004, FR-005
Validator check: `identity`
Schema: `schemas/identity-record.schema.yaml`
Template: `templates/identity-record.template.yaml`

## Purpose

A Tenant Identity Record is the repository-visible declaration of an
agent identity that may participate in Creator-Engine-governed work for a
tenant. A reviewer with only a fresh clone must be able to read this
record and answer:

- which tenant the identity belongs to (`tenant_id`)
- which source host controls the installation (`source_host`)
- which source-host installation is being used (`source_host_installation_id`)
- which agent application and durable actor identity are acting
  (`agent_app_slug`, `agent_actor_id`)
- which runtime/tool and generic role category the actor uses
  (`runtime_tool`, `role_category`)
- which repositories and mutation classes this identity may touch
  (`allowed_repositories`, `mutation_classes`)
- which signing policy applies (`signing_policy`)
- where attestation, ratification, and redaction records are stored
  (`attestation_storage_path`, `ratification_storage_path`,
  `redaction_storage_path`)

If an actor is not named in a conforming identity record, its mutation is
not Creator-Engine-governed and MUST NOT be accepted as such.

## Platform identity vs tenant identity (FR-002)

`tenant_id` names the tenant-level governance identity. It is distinct
from source-host or platform identities such as GitHub installation ids,
bot slugs, or actor ids. Platform identity fields are evidence used to
bind the tenant identity to a concrete source-host actor; they do not
replace the tenant identity.

`platform_identity_ref` is optional and may point at a future separate
platform-identity record. v0.1 records the reference when present but
does not require a separate platform identity document.

## Required fields

All required fields MUST be present and non-empty unless a stricter type
rule below applies.

| Field | Type | FR | Rule |
|---|---|---|---|
| `tenant_id` | string | FR-001 | kebab-case slug matching `^[a-z][a-z0-9-]*$` |
| `source_host` | enum | FR-003 | v0.1 supports `github` |
| `source_host_installation_id` | string | FR-001/FR-003 | non-empty source-host installation identifier |
| `agent_app_slug` | string | FR-001/FR-003 | non-empty application or bot slug |
| `agent_actor_id` | string | FR-001/FR-003 | non-empty durable actor id |
| `runtime_tool` | string | FR-001 | non-empty runtime/tool name |
| `role_category` | enum | FR-005 | one of `source`, `ratifier`, `reviewer`, `architect`, `implementer`, `verifier`, `observer` |
| `authority_context` | object | FR-001/FR-005 | contains `description`, `governing_spec_refs`, `ratifier_authority_refs` |
| `human_ratifier_roles` | array<string> | FR-001/FR-005 | non-empty; an empty array is invalid |
| `mutation_classes` | array<string> | FR-005 | non-empty; class resolution is enforced by mutation-class checks |
| `allowed_repositories` | array<string> | FR-005 | non-empty fully qualified repo identifiers for the source host |
| `signing_policy` | object | FR-001 | contains signing booleans and method |
| `attestation_storage_path` | string | FR-004 | non-empty repo-relative directory path |
| `ratification_storage_path` | string | FR-004 | non-empty repo-relative directory path |
| `redaction_storage_path` | string | FR-004 | non-empty repo-relative directory path |

Optional field: `platform_identity_ref` string.

## Authority context

`authority_context` MUST contain:

- `description`: non-empty human-readable authority rationale.
- `governing_spec_refs`: non-empty array of repo-relative paths naming
  the specs that authorize this identity.
- `ratifier_authority_refs`: non-empty array of repo-relative paths naming
  authority artifacts that declare ratification expectations.

## Signing policy

`signing_policy` MUST contain:

- `commit_signing_required`: boolean.
- `commit_signing_method`: one of `gpg`, `ssh`, `none`.
- `attestation_signing_required`: boolean.

If `commit_signing_required` is `true`, `commit_signing_method` MUST NOT
be `none`.

## Storage path rule (FR-004)

The three storage path fields are repo-relative directory paths. The
identity check resolves them from the repository root and requires the
declared directories to exist. Directories may be empty for a not-yet-used
tenant; missing directories are invalid because reviewers cannot locate
the future records from repository artifacts alone.

## Validator behavior

The `identity` check validates every targeted identity record against
`schemas/identity-record.schema.yaml`, then applies explicit edge-case
rules that must cite this contract:

- missing required fields fail with `FR-001`
- empty `human_ratifier_roles` fails with `FR-001`
- invalid platform/source-host identity shape fails with `FR-003`
- missing storage directories fail with `FR-004`
- missing or malformed authority/allowed-scope fields fail with `FR-005`

Every failure message includes the field/path, an FR code, and this
contract path per FR-027.

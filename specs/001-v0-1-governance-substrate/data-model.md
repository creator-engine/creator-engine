# Data Model: Creator Engine v0.1 Governance Substrate

**Phase**: 1 (Design & Contracts) | **Date**: 2026-05-09

This document enumerates the entities the substrate ships, their fields,
their relationships, the validation rules the validator enforces against
them, and the state transitions that govern lifecycle-bearing entities.

Machine-validated records and sidecars are stored as YAML files.
Human-readable contracts remain Markdown, and the verification-spec
source uses a vanilla Spec Kit `spec.md` plus canonical YAML sidecar.
Field types use JSON Schema vocabulary; the canonical schema for each
machine-validated entity is at `schemas/<entity>.schema.yaml` (shipped
by this feature, not in this document).

---

## Entity 1: Tenant Identity Record

**Source FRs**: FR-001, FR-002, FR-003, FR-005

**File location convention**: `tenants/<name>/identity-record.yml` for
in-repo tenants. Out-of-repo tenants choose their own location; the
contract defines fields, not directories.

**Fields** (required unless marked optional):

| Field                         | Type                           | Constraint |
|-------------------------------|--------------------------------|------------|
| `tenant_id`                   | string (kebab-case slug)       | non-empty; matches `^[a-z][a-z0-9-]*$` |
| `source_host`                 | enum                           | v0.1: `github` (FR-003 reference); future-extension allowed by enum extension |
| `source_host_installation_id` | string                         | non-empty; format depends on `source_host` (e.g. GitHub App installation id) |
| `agent_app_slug`              | string                         | non-empty (e.g. `<tenant>-agent[bot]`) |
| `agent_actor_id`              | string                         | non-empty; the durable actor identity (e.g. GitHub user id of the bot) |
| `runtime_tool`                | string                         | non-empty (e.g. `Claude Code`, `Codex CLI`) |
| `role_category`               | enum                           | one of `source`, `ratifier`, `reviewer`, `architect`, `implementer`, `verifier`, `observer` (FR-015) |
| `authority_context`           | object                         | tenant-shaped; see Authority Context below |
| `human_ratifier_roles`        | array<string>                  | non-empty (an empty array is an FR-001 violation per the spec edge-case) |
| `mutation_classes`            | array<string>                  | each entry MUST be either a baseline class or a declared tenant-extension class (FR-006) |
| `allowed_repositories`        | array<string>                  | each entry is a fully qualified repo identifier scoped to `source_host` |
| `signing_policy`              | object                         | see Signing Policy below |
| `attestation_storage_path`    | string (repo-relative path)    | non-empty (FR-001, FR-020a) |
| `ratification_storage_path`   | string (repo-relative path)    | non-empty (FR-001, FR-020a) |
| `redaction_storage_path`      | string (repo-relative path)    | non-empty (FR-001, FR-020a) |
| `platform_identity_ref`       | string (optional)              | reference to a separate platform-identity record per FR-002, distinguishing platform from tenant identity |

**Authority Context** sub-object:
- `description`: string — tenant-readable explanation of why this
  identity is allowed to act.
- `governing_spec_refs`: array<string> — repo-relative paths to the
  spec(s) that authorize this identity (e.g. this feature's spec).
- `ratifier_authority_refs`: array<string> — repo-relative paths to the
  authority artifact (e.g. authority-matrix-overlay) that names the
  ratifier(s) for this identity.

**Signing Policy** sub-object:
- `commit_signing_required`: bool
- `commit_signing_method`: enum (`gpg`, `ssh`, `none`); `none` only
  permitted when `commit_signing_required` is `false`.
- `attestation_signing_required`: bool — v0.1 records evidence of the
  signing requirement; v0.1 does not implement signature verification
  itself.

**Validation rules** (validator checks):
- `identity.py` — all required fields present and non-empty;
  `human_ratifier_roles` is non-empty (spec edge-case "An attempt to
  bootstrap a tenant with no `human_ratifier_roles`").
- `mutation_class.py` — every entry in `mutation_classes` resolves to a
  declared class (baseline or tenant-extension).
- `attestation_linkage.py` — `attestation_storage_path`,
  `ratification_storage_path`, `redaction_storage_path` resolve to
  existing directories (or are tolerated empty for a not-yet-used
  tenant; missing parent directories are an error).

**Relationships**:
- One Tenant Identity Record → many Mutation Class declarations (by
  reference).
- One Tenant Identity Record → one Authority Matrix Overlay (per
  tenant).
- One Tenant Identity Record → many Attestation/Ratification/Redaction
  Records (rooted at the declared storage paths).

---

## Entity 2: Mutation Class Declaration

**Source FRs**: FR-006, FR-007, FR-008

**File locations**:
- Baseline (substrate-shipped): encoded in
  `schemas/mutation-class.schema.yaml` and described in
  `docs/contracts/mutation-class-taxonomy.md`.
- Tenant-extension: `tenants/<name>/mutation-classes.yml` (one document
  per tenant; multiple class entries within).

**Fields** (per class entry):

| Field                  | Type                                             | Constraint |
|------------------------|--------------------------------------------------|------------|
| `name`                 | string                                           | non-empty; lowercase kebab-case; for baseline classes one of `docs`, `code`, `schema`, `deploy`, `governance`, `identity`, `security`, `attestation`, `redaction` |
| `is_baseline`          | bool                                             | `true` for the nine baseline classes, `false` for tenant extensions |
| `action_vocabulary`    | array<string>                                    | each action is a member of the substrate's reserved-action vocabulary (FR-006); see Reserved Actions below |
| `agent_permitted_actions` | array<string>                                 | subset of `action_vocabulary`; for FR-008-listed privileged classes (`deploy`, `publish`, credential-issue/revoke, org/tenant/repo settings, governance, security, identity, attestation-gate weakening, redaction-gate weakening) this MUST NOT include any merge/deploy/publish action absent explicit human ratification |
| `human_ratification_required` | bool                                      | MUST be `true` for the privileged classes named in FR-008 |
| `description`          | string                                           | non-empty rationale, repo-readable |

**Reserved-action vocabulary** (FR-006, baseline; tenant extensions
MUST draw their actions from this vocabulary):

`propose`, `edit`, `commit`, `open_pr`, `attest`, `advise_only`,
`merge`, `deploy`, `publish`, `issue_credential`, `revoke_credential`,
`alter_org_settings`, `alter_tenant_settings`, `alter_repo_settings`,
`approve_redaction`, `weaken_attestation_gate`,
`weaken_redaction_gate`.

**Validation rules**:
- `mutation_class.py` —
  - All nine baseline classes are present in any conformant taxonomy
    bundle (substrate ships them; tenants MUST NOT remove them).
  - Tenant-extension classes (`is_baseline: false`) MUST NOT reuse a
    baseline class name.
  - Every `action_vocabulary` entry is in the reserved-action
    vocabulary above.
  - `agent_permitted_actions` ⊆ `action_vocabulary`.
  - For privileged classes (FR-008), `agent_permitted_actions` does
    NOT contain `merge`, `deploy`, `publish`, `issue_credential`,
    `revoke_credential`, `alter_org_settings`,
    `alter_tenant_settings`, `alter_repo_settings`,
    `approve_redaction`, `weaken_attestation_gate`, or
    `weaken_redaction_gate`.

**Relationships**:
- Many Mutation Class Declarations ← one Mutation Class Taxonomy
  bundle (substrate baseline + zero or more tenant extensions).
- Each Spec Wrapper / Plan Wrapper / Tasks Wrapper references one
  declared mutation class by `name`.

---

## Entity 3: Spec Wrapper Sidecar (`spec.creator-engine.yml`)

**Source FRs**: FR-009, FR-010, FR-012, FR-012a, FR-013a

**File location**: Adjacent to `spec.md` in the same feature folder
(directory adjacency rule, research Decision 4).

**Fields**:

| Field                      | Type                                 | Constraint |
|----------------------------|--------------------------------------|------------|
| `id`                       | string                               | non-empty; unique across the substrate (duplicate detection per FR-027a) |
| `title`                    | string                               | non-empty |
| `tenant`                   | string                               | resolves to a `tenant_id` of an Identity Record |
| `owner_role`               | string                               | one of the declared role categories or a tenant-overlay role |
| `status`                   | enum                                 | exactly one of `draft`, `ready`, `in_progress`, `verified`, `ratified`, `done` (FR-013a) |
| `spec_type`                | enum                                 | one of `decision_record`, `implementation_spec`, `research_report`, `handoff`, `retro`, `test_spec`, `tenant_config` (FR-011); unknown types rejected per the spec edge-case |
| `mutation_class`           | string                               | declared class name |
| `permitted_actions`        | array<string>                        | subset of the class's `action_vocabulary` |
| `scope`                    | string (markdown)                    | non-empty |
| `acceptance_criteria`      | array<string>                        | non-empty |
| `verification`             | object                               | non-empty; `method` (string) and `evidence_refs` (array<string>) |
| `ratification_required`    | bool                                 | required |
| `identity_policy_ref`      | string (repo-relative path)          | resolves to an existing identity record |
| `attestation_record_ref`   | string (optional, repo-relative)     | required by `attestation_linkage` check once status reaches `verified` |
| `ratification_record_ref`  | string (optional, repo-relative)     | required for `ratified`/`done` |

**Compatibility-vs-canonical rule** (FR-009): If a corresponding
display field exists in vanilla Spec Kit `spec.md` frontmatter (e.g. a
title) and disagrees materially with the sidecar value, the validator
emits a `WARN` or `FAIL` per the field's schema rule; sidecar values
are canonical for governance fields, never silently overridden.

**Validation rules**:
- `sidecar_conformance.py` — schema-level field presence and types.
- `duplicate_spec_id.py` — every `id` is unique across the repo.
- `definition_of_ready.py` — for `status >= ready`, `scope`,
  `acceptance_criteria`, and `verification` are non-empty (FR-013).
- `mutation_class.py` — `permitted_actions` ⊆ class action vocabulary.
- `lifecycle.py` — see State Transitions below.

**Relationships**:
- Spec Wrapper Sidecar 1 ↔ 1 Spec Kit `spec.md` (by directory
  adjacency).
- Spec Wrapper Sidecar references → Identity Record (via
  `identity_policy_ref`), Mutation Class (via `mutation_class`),
  Attestation Record (via `attestation_record_ref`), Ratification
  Record (via `ratification_record_ref`).

---

## Entity 4: Plan Wrapper Sidecar (`plan.creator-engine.yml`)

**Source FRs**: FR-012a, FR-012b

**File location**: Adjacent to `plan.md`.

**Fields**:

| Field                            | Type                            | Constraint |
|----------------------------------|---------------------------------|------------|
| `spec_ref`                       | string (repo-relative)          | resolves to a Spec Wrapper Sidecar |
| `plan_mutation_class_summary`    | array<string>                   | each entry is a declared class touched by the plan |
| `plan_permitted_actions_summary` | array<string>                   | subset of the union of permitted actions across the plan's classes |
| `verification_plan`              | object                          | `method` and `evidence_refs[]` describing how plan-level verification will be performed |
| `ratification_required`          | bool                            | mirrors spec; if `true` the matching ratification record is required before `ratified` |
| `identity_policy_ref`            | string (repo-relative)          | resolves to an Identity Record |

**Validation rules**:
- `sidecar_conformance.py` — schema-level field presence and types.
- `mutation_class.py` — every class in `plan_mutation_class_summary`
  is declared.

---

## Entity 5: Tasks Wrapper Sidecar (`tasks.creator-engine.yml`)

**Source FRs**: FR-012a, FR-012b

**File location**: Adjacent to `tasks.md`.

**Fields**:

| Field           | Type                           | Constraint |
|-----------------|--------------------------------|------------|
| `spec_ref`      | string (repo-relative)         | resolves to a Spec Wrapper Sidecar |
| `tasks`         | array<TaskEntry>               | non-empty |

**TaskEntry** sub-object:

| Field                              | Type                  | Constraint |
|------------------------------------|-----------------------|------------|
| `id`                               | string                | unique within this sidecar |
| `title`                            | string                | non-empty |
| `mutation_class`                   | string                | declared class name |
| `permitted_actions`                | array<string>         | subset of class action vocabulary |
| `verification_evidence_ref`        | string                | repo-relative path or anchor |
| `ratification_or_approval_ref`     | string (optional)     | required for ratification-relevant tasks (FR-007/FR-016/FR-017) |
| `author_actor_id`                  | string                | resolves to an `agent_actor_id` or named human |
| `approver_actor_id`                | string (optional)     | resolves to a distinct actor; equality with `author_actor_id` is an FR-007 violation |

**Validation rules**:
- `sidecar_conformance.py` — schema-level field presence and types.
- `mutation_class.py` — class/action mismatch detection.
- `ratification.py` — author/approver separation (FR-007).

---

## Entity 6: Authority Matrix

**Source FRs**: FR-015, FR-016

**File locations**:
- Baseline (substrate-shipped): `docs/contracts/authority-matrix.md`
  with a normative YAML block (or a sibling `schemas/`-validated YAML)
  carrying one row per baseline mutation class and a row per role
  category.
- Tenant overlay: `tenants/<name>/authority-matrix-overlay.yml`.

**Fields** (per row):

| Field                          | Type                          | Constraint |
|--------------------------------|-------------------------------|------------|
| `role_category`                | enum                          | one of `source`, `ratifier`, `reviewer`, `architect`, `implementer`, `verifier`, `observer` |
| `tenant_role_name`             | string (optional)             | overlay-only; populated by tenant fixtures |
| `allowed_instruction_sources`  | array<string>                 | non-empty |
| `allowed_mutation_classes`     | array<string>                 | each entry is a declared class |
| `required_ratifier_role`       | string                        | resolves to a `role_category` or tenant overlay; for FR-008 privileged classes MUST be a human role |
| `allowed_communication_surfaces` | array<string>               | non-empty (e.g. `repo_pr`, `repo_issue`, named chat surface) |
| `required_audit_artifacts`     | array<string>                 | non-empty (e.g. `attestation_record`, `ratification_record`) |

**Validation rules**:
- Baseline matrix MUST contain at least one row for every baseline
  mutation class (FR-015 "concrete rows for every baseline mutation
  class").
- Tenant overlays MUST NOT reuse a baseline `role_category` to
  redefine its semantics; tenant role names appear only in
  `tenant_role_name`.

**Relationships**:
- Authority Matrix row(s) ← Mutation Class (via
  `allowed_mutation_classes`).
- Authority Matrix row(s) ← Identity Record (via `role_category`).

---

## Entity 7: Ratification Flow

**Source FRs**: FR-016, FR-017, FR-018

**File location**:
- Generic flow rules: `docs/contracts/ratification-flow.md` (no
  tenant-specific surfaces).
- Tenant flow: `tenants/<name>/ratification-flow.yml`.

**Fields** (per flow entry, one per mutation class per tenant):

| Field                        | Type             | Constraint |
|------------------------------|------------------|------------|
| `mutation_class`             | string           | declared class name |
| `required_ratifier_role`     | string           | resolves to authority matrix; for FR-008 privileged classes MUST be a human role |
| `valid_ratification_surfaces` | array<string>   | each surface is one named in the authority matrix's `allowed_communication_surfaces` for the same row |
| `evidence_required`          | array<string>    | non-empty (e.g. `verification_evidence`, `review_findings`, `attestation_record`) |

**Validation rules**:
- `ratification.py` —
  - For every spec at status `ratified` or `done`, a matching
    Ratification Record exists at the tenant's
    `ratification_storage_path`.
  - The record's surface matches a `valid_ratification_surfaces`
    entry for the spec's mutation class.
  - The record's ratifier is distinct from the spec's author (FR-007).
  - Agent-authored review text is NOT recorded as ratification for
    FR-008 privileged classes (FR-017).
  - "Go ahead"-style messages on un-designated surfaces are not
    accepted as ratification (FR-018).

---

## Entity 8: Attestation Record

**Source FRs**: FR-004, FR-005, FR-020a

**File location**: Under the tenant's `attestation_storage_path` from
the Identity Record. Filename: `<YYYY-MM-DD>-<mutation-id>.yml`. One
record per mutation.

**Fields**:

| Field                      | Type                       | Constraint |
|----------------------------|----------------------------|------------|
| `mutation_id`              | string                     | unique across the tenant's attestation records |
| `state`                    | enum                       | `pre_merge` or `finalized` (research Decision 13) |
| `spec_ref`                 | string                     | resolves to a Spec Wrapper Sidecar |
| `agent_identity_ref`       | string                     | resolves to a tenant identity record entry |
| `mutation_class`           | string                     | declared class name |
| `permitted_actions`        | array<string>              | subset of class action vocabulary |
| `verification_evidence`    | object                     | `method`, `evidence_refs[]` (same shape as Entity 12) |
| `ratifier_identity_ref`    | string                     | resolves to the actor (human or role) that ratified; MUST be distinct from the author identity |
| `merge_reference`          | string (conditional)       | required when `state == finalized`; absent when `state == pre_merge` |
| `created_at`               | string (date)              | `YYYY-MM-DD`; matches the filename's date prefix |

**Validation rules**:
- `attestation_linkage.py` —
  - For every spec at status `verified`, a `pre_merge` attestation
    exists.
  - For every spec at status `done`, a `finalized` attestation exists
    with `merge_reference` populated.
  - The author actor recorded in the spec/tasks sidecar is NOT the
    `ratifier_identity_ref`.
  - The `mutation_class` matches the spec's declared class.

**Relationships**:
- Attestation Record 1 → 1 Spec Wrapper Sidecar (via `spec_ref`).
- Attestation Record 1 → 1 Identity Record (via
  `agent_identity_ref`).
- Attestation Record 1 → 1 Ratification Record (by mutation_id;
  ratifier corroborated against ratification record's actor).

---

## Entity 9: Ratification Record

**Source FRs**: FR-016, FR-017, FR-020a

**File location**: Under the tenant's `ratification_storage_path`.
Filename: `<YYYY-MM-DD>-<mutation-id>.yml`. One record per
ratification.

**Fields**:

| Field                       | Type                | Constraint |
|-----------------------------|---------------------|------------|
| `mutation_id`               | string              | matches the corresponding attestation record's mutation_id |
| `spec_ref`                  | string              | resolves to a Spec Wrapper Sidecar |
| `mutation_class`            | string              | matches the spec's declared class |
| `ratifier_actor_id`         | string              | non-empty; for FR-008 privileged classes MUST be a human |
| `ratifier_role`             | string              | resolves to authority matrix `required_ratifier_role` |
| `surface`                   | string              | matches a `valid_ratification_surfaces` entry |
| `evidence_reviewed`         | array<string>       | non-empty; references to verification artifacts |
| `decision`                  | enum                | `accept` (v0.1 records the positive case; rejection is implicit by the absence of a record) |
| `created_at`                | string (date)       | `YYYY-MM-DD` |

**Validation rules**:
- `ratification.py` — author/approver separation, surface validity,
  human ratifier for FR-008 classes.

---

## Entity 10: Redaction Gate Policy

**Source FRs**: FR-019, FR-020, FR-021

**File location**: `docs/contracts/redaction-gate-policy.md` defines
the generic policy fields. Tenants do not override the policy in v0.1;
v0.1 defines policy fields and validation behavior only.

**Fields** (per policy version):

| Field                          | Type                | Constraint |
|--------------------------------|---------------------|------------|
| `policy_version`               | string              | semantic version |
| `applies_to_export_intents`    | array<string>       | enum members: `public`, `nda_visible` |
| `required_redaction_outputs`   | array<string>       | non-empty (fields that the redaction record must populate) |
| `approver_constraints`         | object              | author/approver separation rules (FR-021) |

**Validation rules**:
- `redaction_gate.py` —
  - Any artifact declaring `export_intent: public` or
    `export_intent: nda_visible` MUST reference a Redaction Record
    bound to a known `policy_version`.
  - The redaction approver MUST NOT be the author of the underlying
    artifact (FR-021).

---

## Entity 11: Redaction Record

**Source FRs**: FR-020, FR-020a, FR-021

**File location**: Under the tenant's `redaction_storage_path`.
Filename: `<YYYY-MM-DD>-<redaction-or-artifact-id>.yml`. One record
per redaction.

**Fields**:

| Field                  | Type                   | Constraint |
|------------------------|------------------------|------------|
| `redaction_id`         | string                 | unique across the tenant's redaction records |
| `source_artifact_ref`  | string                 | repo-relative path to the artifact being redacted |
| `redacted_regions`     | array<object>          | each entry: `{path: str, locator: str, reason: str}` |
| `approver_actor_id`    | string                 | non-empty; MUST NOT equal the source artifact's author |
| `approver_role`        | string                 | resolves to an authority matrix role |
| `policy_version`       | string                 | resolves to a Redaction Gate Policy version |
| `created_at`           | string (date)          | `YYYY-MM-DD` |

**Validation rules**:
- `redaction_gate.py` — see Entity 10.

---

## Entity 12: Verification Evidence (sub-object referenced by other entities)

**Source FRs**: FR-014

Not a stand-alone file; appears as the `verification` field of Spec
Wrapper Sidecar, the `verification_evidence` field of Attestation
Record, and the `evidence_reviewed` array of Ratification Record.

**Shape**:
- `method`: string — describes how the evidence was produced (e.g.
  "validator pass on bundled examples", "code review by reviewer X",
  "test suite Y passed locally on commit Z").
- `evidence_refs`: array<string> — repo-relative paths or git refs
  pointing at the evidence artifacts (test logs, validator
  `--json` output, review notes).

**Validation rules**:
- `definition_of_done.py` — rejects self-claims (a spec at `verified`
  whose `verification.evidence_refs` is empty or whose only ref is
  authored by the same agent identity is rejected per FR-014's
  "rejects self-claims of completion").

---

## Entity 13: LIMITLESS Dogfood Fixture (composite entity, not a single file)

**Source FRs**: FR-022, FR-023, FR-024, FR-024a

**File location**: `tenants/limitless/`

**Composition**: A populated set of the above entities for the
LIMITLESS tenant — one Identity Record, one Mutation Classes
declaration (baseline overlay if needed), one Authority Matrix
Overlay, one Ratification Flow, one canonical identifier list
(`limitless-identifiers.yml`), and the three storage roots
(`attestations/`, `ratifications/`, `redactions/`).

**Validation rules**:
- All standard entity rules apply.
- Additionally: SC-005 — zero fields marked `TBD`/deferred/unresolved.
- `no_limitless_strings.py` — none of the identifiers in
  `limitless-identifiers.yml` appear under the four generic-contract
  paths (FR-024, SC-004).

---

## State Transitions: Six-State Lifecycle

**Source FRs**: FR-013, FR-013a, FR-014

```
[draft] --DoR-pass--> [ready] --authorized-take--> [in_progress] \
                                                                  \
   --evidence-recorded-by-author--> [verified] --ratified-by-distinct-actor--> [ratified]
                                                                                 |
                                                                       merge + finalize attestation
                                                                                 |
                                                                                 v
                                                                              [done]
```

| From          | To              | Gate (validator check)                                                              |
|---------------|-----------------|-------------------------------------------------------------------------------------|
| `draft`       | `ready`         | Definition of Ready: `scope`, `acceptance_criteria`, `verification` non-empty (FR-013) |
| `ready`       | `in_progress`   | Authority matrix permits the actor to take the work for this mutation class (FR-015) |
| `in_progress` | `verified`      | Author records `verification.evidence_refs[]`; author ≠ ratifier (FR-007/FR-014)    |
| `verified`    | `ratified`      | Ratification Record exists; ratifier_actor ≠ author; surface valid; for FR-008 classes, ratifier is human |
| `ratified`    | `done`          | `pre_merge` attestation exists, mutation merged, attestation `state` advanced to `finalized` with `merge_reference` |

**Forbidden transitions** (validator errors):
- Any skip (e.g. `draft → in_progress`, `ready → verified`).
- Any backflow (e.g. `done → ratified`).
- Any "split-actor" that records the same actor as both author and
  ratifier across the `verified → ratified` gate (FR-007).

**Validator check**: `lifecycle.py` walks each spec sidecar, derives
the historical sequence of statuses from git log on the sidecar file
(no external state needed), and confirms each transition was gated as
above. Out-of-order transitions are surfaced with the offending FR
cited.

---

## Entity Relationship Diagram (logical)

```
Identity Record ───┐
                   │ 1..N references
                   ▼
              Spec Wrapper Sidecar ──── 1:1 ──── spec.md
                   │
         ┌─────────┼─────────┬──────────────┐
         │         │         │              │
         ▼         ▼         ▼              ▼
     Plan Wrapper  Tasks Wrapper   Attestation Record   Ratification Record
                                    (pre_merge/finalized)         │
                                            │                     │
                                            └────── joined by ────┘
                                                  mutation_id

Mutation Class Taxonomy ───── declares classes referenced by ─────► Spec/Plan/Tasks/Attestation/Ratification

Authority Matrix ───── names ratifier role for ─────► Mutation Class (per row)

Ratification Flow ───── names valid surfaces for ─────► Mutation Class (per tenant)

Redaction Gate Policy ──── governs ────► artifacts with export_intent
                                              │
                                              ▼
                                        Redaction Record (one per redaction)
```

All edges resolve to repo-relative paths or to declared identifiers
(class names, role categories, mutation ids). No edge resolves to an
external system in v0.1.

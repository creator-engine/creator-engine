# Creator Engine v2.0 Operating-mode Substrate

Gate: G2.002.1 (active slice; predecessor G2.002.0 merged)

Status: draft

## Goal

Define the v2 operating-mode substrate used by later runtime, connector, queue,
and autonomy surfaces while preserving the Operator-only privileged floor.

Slice G2.002.0 landed the policy substrate (enums, policy schema, validator,
fixtures, spec/ADR/architecture docs). Slice G2.002.1 propagates that substrate
into runtime carriers — Assignment Envelope representation, active-work-ledger
records, and the `ce lane launch` default/refusal behavior — without weakening
the Operator-only privileged floor in any mode.

## Functional Requirements

- FR-001: The substrate MUST define `operating_mode` values `strict`, `auto`, and `transcendence`.
- FR-002: The substrate MUST define `autonomy_class` values for manual, supervised, delegated non-privileged, Operator-ratified privileged, and reserved future agent-ratification states.
- FR-003: Migrated v1 tenants MUST default to `strict`.
- FR-004: `auto` mode MUST require an Operator-ratified policy pointer before activation.
- FR-005: `transcendence` mode MUST require an Operator-ratified policy pointer before activation.
- FR-006: Privileged mutation classes MUST require `operator` as the ratifier role in every mode.
- FR-007: `agent_reviewer` MAY produce advisory evidence but MUST NOT ratify privileged classes.
- FR-008: `agent_ratifier` MUST remain reserved-inactive; active authority bindings MUST fail closed.
- FR-009: Emergency override MUST remain Operator-only.
- FR-010: CE operating-mode metadata MUST live in adjacent `spec.ce.yml` sidecars, not inline Markdown metadata.
- FR-011: G2.002.0 MUST stop at docs, schema, validator, examples, and specification substrate.
- FR-012: Runtime carrier propagation into lane, ledger, queue, connector, or assignment-envelope records is G2.002.1+ work.

## Functional Requirements — G2.002.1 runtime carriers

- FR-013: The Active-Work Ledger record schema MUST carry optional `operating_mode`, `autonomy_class`, and `lane_kind` runtime-carrier fields under the existing record shape.
- FR-014: The schema MUST define `lane_kind` values `read-only`, `implementation`, `review`, `approval`, `merge`, and `audit`.
- FR-015: Runtime-carrier records MUST be able to carry an inherited ratification-evidence pointer (`ratification_evidence_ref`) for elevated modes and privileged lane kinds.
- FR-016: `ce lane launch` MUST default `operating_mode` to `strict`.
- FR-017: `ce lane launch` MUST refuse `auto` or `transcendence` without an Operator-ratified tenant policy, before any tmux spawn, Pane Registry write, or ledger write.
- FR-018: `ce lane launch` MUST refuse a privileged class that names `agent_ratifier` or an advisory role as the ratifier, before any side effect.
- FR-019: Runtime carriers MUST preserve the Operator-only privileged floor in every mode: no privileged-class relaxation, no agent ratification, advisory-only `agent_reviewer`, reserved-inactive `agent_ratifier`, and Operator-only emergency override.
- FR-020: Absent or migrated operating-mode carriers MUST resolve to `strict`; migration MUST NOT infer `auto` or `transcendence`.
- FR-021: The carrier extension MUST be additive: `schema_version` is extended to include `"4"` while pre-v4 (`"1"`–`"3"`) records continue to validate unchanged.
- FR-022: Review/approval/merge lane kinds MUST be representable as carriers and documented as downstream-enforced; G2.002.1 MUST NOT implement PR-review enforcement.
- FR-023: The Assignment Envelope representation MUST carry operating mode, autonomy class, and ratification pointer as pure carriers that introduce no new authority.

## Non-goals

- No G2.001.4 crosswalk-register mutation.
- No merge readiness; this substrate remains dependency-gated on G2.001.4.
- G2.002.1 carries review/approval/merge lane kinds but does NOT implement PR-review, approval, or merge enforcement; that is downstream work.
- G2.002.1 activates neither `auto` nor `transcendence`, authors no Operator-ratified tenant policy, and binds no `agent_ratifier`.

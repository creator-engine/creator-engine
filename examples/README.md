# Validator Examples

Examples are split into two directories:

- `well-formed/` contains project-agnostic fixtures expected to pass validation.
- `malformed/` contains intentionally invalid fixtures expected to fail with specific FR citations.

The `check-examples` command is successful only when all well-formed fixtures pass and every malformed fixture fails with its documented FR citation. Raw validation against `examples/malformed/` should exit non-zero.

## Malformed fixture catalog

Malformed fixtures are added story-by-story. Each fixture must remain intentionally invalid and must fail with the listed FR citation once its story check lands.

| Fixture | Intentional violation | Expected citation |
|---|---|---|
| `identity-record.missing-fields.yml` | Missing or empty tenant identity fields, including empty `human_ratifier_roles` | `FR-001` |
| `spec.creator-engine.missing-acceptance.yml` | Ready-or-later spec sidecar omits `acceptance_criteria` | `FR-013` |
| `duplicate-spec-id/` | Two spec sidecars declare the same `id` | `FR-027a` |
| `tasks.creator-engine.class-action-mismatch.yml` | Task declares an action outside its mutation class vocabulary | `FR-006`, `FR-027a` |
| `self-ratification.yml` | Ratifier/approver identity equals the author identity | `FR-007` |
| `attestation-record.missing-ratifier.yml` | Attestation omits ratifier identity linkage | `FR-004` |
| `lifecycle-skipped-state.yml` | Lifecycle status skips required intermediate states | `FR-013a` |
| `redaction-record.missing-policy-version.yml` | Redaction record omits required policy version | `FR-020` |
| `runtime-evidence/agent-action-bad-op.yml` | v3 G-4 `runtime_agent_action` record carries an `op` outside the operation vocabulary | `runtime_evidence_schema_violation` |

If a new malformed fixture is added, update this table before relying on `check-examples` as acceptance evidence.

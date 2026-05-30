# ADR-V2-002-1: Operating-mode runtime carriers

Status: Accepted for G2.002.1 draft (runtime carriers; predecessor ADR-V2-002)

## Context

G2.002.0 (ADR-V2-002, PR #85, merged) landed the operating-mode policy
substrate: the `strict` / `auto` / `transcendence` mode enum, the
`autonomy_class` enum, the `operating-mode-policy` schema, the
`operating_mode_policy` validator, fixtures, and spec/architecture text. That
substrate is shape-only — it deliberately did not propagate operating mode into
any live runtime surface.

G2.002.1 must carry that substrate into the runtime: the Assignment Envelope
representation, Active-Work Ledger records, and the `ce lane launch` default and
refusal behavior. It must do so without weakening the Operator-only privileged
floor and without activating any elevated mode.

## Decision

1. **Carriers are additive, not authoritative.** The Active-Work Ledger record
   schema gains optional `operating_mode`, `autonomy_class`, `lane_kind`, and
   `ratification_evidence_ref` fields, and `schema_version` is extended to
   include `"4"`. Pre-v4 records continue to validate unchanged. The carriers
   record posture; the Assignment Envelope and Operator ratification remain the
   substantive authority.

2. **No new authority schema for the Assignment Envelope.** Rather than
   introduce a standalone `assignment-envelope` JSON Schema (which has never
   existed and would risk minting new authority), the envelope mode/autonomy/
   ratification carriers ride the existing Active-Work Ledger carrier fields and
   are documented in `ASSIGNMENT_ENVELOPE_TEMPLATE.md` as pure carriers. This
   keeps the new-surface footprint minimal and introduces no new authority.

3. **`lane_kind` is a new, distinct enum** — `read-only`, `implementation`,
   `review`, `approval`, `merge`, `audit` — separate from `pane_label`. It lets
   a downstream reviewer/approver/merger lane be a *different* lane kind from the
   implementer lane. G2.002.1 only *carries* the field; PR-review enforcement is
   downstream work.

4. **`strict` is the runtime default; elevation fails closed.** `ce lane launch`
   defaults `--operating-mode` to `strict`. `auto`/`transcendence` are refused
   unless an Operator-ratified tenant policy ratifies the requested mode. A
   privileged class naming `agent_ratifier` or an advisory role as ratifier is
   refused. Every new refusal is raised *before* any tmux spawn, Pane Registry
   write, or ledger write, mirroring the existing `G3-*` refusal ordering. New
   refusal codes use the `G2-*` family.

5. **A dedicated carrier validator enforces the floor.** A new
   `operating_mode_runtime_carriers` check validates carrier conformance and
   floor preservation (strict default, elevation-requires-ratification,
   reserved-inactive `agent_ratifier`, advisory-only reviewer, Operator-only
   override), reusing the `operating_mode_policy` substrate helpers rather than
   re-deriving authority semantics.

## Consequences

- The Operator-only privileged floor is preserved in every mode; this ADR
  ratifies no floor relaxation, activates no elevated mode, and binds no
  `agent_ratifier`.
- Absent or migrated carriers resolve to `strict`; migration never infers
  elevation.
- Review/approval/merge lane kinds are representable and documented as
  downstream-enforced; PR-review enforcement is explicitly out of scope.
- This ADR records rationale only. It ratifies nothing by itself; the scoped
  authority is the Operator-ratified G2.002.1 execution prompt recorded in the
  feature 002 `spec.ce.yml` `authority_basis`.

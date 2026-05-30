# Creator Engine v2.0 Operating-mode Substrate

Gate: G2.002.0  
Status: draft

## Goal

Define the v2 operating-mode substrate used by later runtime, connector, queue,
and autonomy surfaces while preserving the Operator-only privileged floor.

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

## Non-goals

- No runtime CLI or active-work-ledger operating-mode propagation.
- No G2.001.4 crosswalk-register mutation.
- No merge readiness; this substrate remains dependency-gated on G2.001.4.

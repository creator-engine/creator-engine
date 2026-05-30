# ADR-V2-002: Operating-mode substrate before runtime carrier propagation

Status: Accepted for G2.002.0 draft substrate

## Context

Creator Engine v2 needs explicit operating-mode metadata before any later runtime
surface can safely support auto-mode. The substrate must make `strict`, `auto`,
and `transcendence` visible while preserving the Operator-only privileged floor.

## Decision

G2.002.0 defines the operating-mode policy schema, sidecar field, validator,
examples, and specification text. `auto` and `transcendence` require an
Operator-ratified policy pointer. `agent_reviewer` remains advisory-only and
`agent_ratifier` remains reserved-inactive.

## Consequences

- Draft PR authoring can proceed before G2.001.4 lands.
- Merge remains dependency-gated on G2.001.4 and later reconciliation.
- Runtime carrier propagation into lane/ledger/envelope records is deferred to
  G2.002.1 and needs separate Operator ratification.

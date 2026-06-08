# Contract: Scope — the coordination-layer atom (G-6)

**Status:** Canonical. Enforced by the `ce_scope` check; the pure coordination
substrate is `creator_engine_validator/coordination.py`.

## Purpose

The **Scope** is the v3 coordination layer's ephemeral **atomic unit of work** —
the OUTER loop ("what work, who ratifies"). A Scope is a ratifiable, scope-boxed
task with testable acceptance criteria, a Shape-Up **appetite**, and an isolated
execution. **A ratified, DoR-valid Scope dispatches ONE isolated run** governed by
the agent-interaction contract (G-4) and the tokenomics gate (G-5). The Scope's
`execution` is the seam where the outer loop meets the inner per-run governance.

This is the CI-pure **idea→governed-delivery spine, Scope-only**. The live dispatch
(actually spawning a run), the durable **Skill** axis, and the
finding-schema/discard-on-drift gate are named deferred follow-ons.

## The Scope atom

`schemas/scope.schema.yaml` — value-free fields:

- `intent` — the framed problem/spec (the `Frame` output).
- `acceptance_criteria` — testable criteria; the DoR core and test-first oracle.
- `appetite` — a Shape-Up **fixed effort budget** (not an estimate); seeds the
  per-run spend cap (below).
- `mutation_class` — the risk tier (drives the back gate).
- `ratification` — the betting-table attestation (value-free opaque digests).
- `skill_refs?` / `crosswalk_parent?` — optional forward/up refs (Skill axis +
  crosswalk traceability are deferred / light).
- `state` — the conserved mechanical spec-lifecycle (below).

## Stage vocabulary (CANON — conserve the machine, derive the skin)

Per `docs/architecture/stage-vocabulary.md`, the Scope's mechanical `state` is the
**conserved spec-lifecycle** — `draft → ready → in_progress → verified → ratified →
done` — conserved **verbatim** (zero new enums). The user-facing cognitive phase
**Frame → Shape → Build → Review → Ship** is a **presentation skin** *derived* from
`state` via the canon dual-mapping (`coordination.cognitive_phase` /
`project_scope_state`). The optional `phase` field is a cached projection the
`ce_scope` check **forces to equal the derivation** — the skin can never drift from
the machine, and (being enum-constrained) can never become a third vocabulary.

| Mechanical `state` | Cognitive phase | Board |
| --- | --- | --- |
| `draft` | Frame | BACKLOG |
| `ready` | Shape | READY |
| `in_progress` | Build | RUN |
| `verified` | Review | REVIEW |
| `ratified` / `done` | Ship | MERGE |

`state` is **state-as-projection** — derived from committed signals by
`coordination.project_scope_state`, never a hand-set FSM value. `ready` requires
BOTH the DoR satisfied AND the bet placed.

## The two-end, risk-tiered gate chain

- **Front gate (Shape→Build):** a Scope cannot dispatch until `intent +
  acceptance_criteria + appetite + mutation_class` are present & valid
  (Definition-of-Ready) **and** a ratifier places the bet (`ratification`).
  Spec quality is the #1 success factor — enforced. `coordination.assemble_dispatch`
  **REFUSES** (`not_ready` / `not_ratified`) otherwise.
- **Middle (Build/Review):** `execution` is governed per-action by G-4
  (`runner.audit_overlay.decide`), metered by G-5 (`runner.spend_gate`), and graded
  by CI (acceptance criteria → test scenarios, test-first).
- **Back gate (Ship):** the `mutation_class`-tiered `human_ratification_required`
  ratified-merge + branch-protection independent review (existing machinery — the
  Scope's `mutation_class` drives it; G-6 builds no new back-gate machinery).

## The appetite → tokenomics-cap join (the G-5 link)

`coordination.appetite_to_spend_envelope` is the clean join between Shape-Up
planning and the G-5 tokenomics gate: a Scope's `appetite {amount, unit}` becomes a
`run`-scope `spend_envelope` (`{scope: "run", amount, unit, window}`) that the G-5
`spend_gate.admit` / `meter_and_check` enforce **unchanged**. `assemble_dispatch`
merges it **additively** into the run's `runtime_policy.spend_envelopes` — alongside
any operator-set `global`/`fleet` envelopes; most-restrictive-wins still holds. See
`docs/contracts/spend-envelope.md`. (A size-enum→amount table, read-live, is a
deferred enhancement.)

## The guard — `ce_scope`

A check over Scope records (`kind: scope-record`). Predicates:

- `VAL-SCOPE-SCHEMA` — the record shape (`schemas/scope.schema.yaml`).
- `VAL-SCOPE-DOR-INCOMPLETE` — a ready-or-later Scope missing the DoR core
  (`acceptance_criteria` / `appetite`).
- `VAL-SCOPE-APPETITE-INVALID` — an appetite not derivable to a `run`-scope
  envelope (`amount > 0`, `unit ∈ {$,%}`).
- `VAL-SCOPE-RATIFICATION-UNBOUND` — a ready-or-later Scope without a valid
  value-free bet ratification.
- `VAL-SCOPE-STATE-INCONSISTENT` — a stored cognitive `phase` that drifts from the
  canon derivation for its `state`.

Green-on-day-one (no Scope artifacts in the repo yet → trivially green). A draft
Scope being framed/shaped may omit the DoR fields (mirrors `definition_of_ready`).

## Value-free invariant

A Scope carries intent / acceptance-criteria / appetite / mutation_class / opaque
ratification digests / optional shape-only refs — **never** a credential, secret
value, raw account, host, or installation identifier.

## Standing requirements honored

- **G-4.1** (`docs/contracts/v3-naming-hygiene.md`): the v3 surface stays
  residue-clean (`v3_naming_hygiene` 0/0 — `coordination` + `schemas/scope.schema.yaml`
  are clean) and any v3 local state goes under `.ce/state` (here the backlog is just
  committed Scope artifacts + state-as-projection — no new state file).
- **G-5** (`docs/contracts/spend-envelope.md`): the appetite→cap join feeds the
  spend gate unchanged.
- **#161** (`docs/architecture/stage-vocabulary.md`): the state/phase vocabulary is
  authored in the ratified canon; no third vocabulary.

## Deferred follow-ons (named)

The live Scope dispatch (spawn a run) · the durable **Skill** axis · the
finding-schema + discard-on-drift gate · the crosswalk-register `scope_mappings`
axis · a backlog index register · a spine-level scope-dispatch attestation record.

See also: `docs/architecture/stage-vocabulary.md`,
`~/Documents/ce-coordination-hierarchy-design-20260606.md` (the pinned design),
`docs/contracts/spend-envelope.md`, `runner/audit_overlay.py` (G-4).

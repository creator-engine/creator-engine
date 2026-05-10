# Contract: Six-State Spec Lifecycle State Machine

**Source FRs**: FR-013, FR-013a, FR-014

## Purpose

Defines the spec status lifecycle and the gates between states, so that
ratification (the `verified → ratified` boundary) is the lifecycle-
level enforcement of author/approver separation (FR-007).

## Implementation surface

- `docs/contracts/lifecycle-state-machine.md` — diagram + transition
  rules.
- `docs/contracts/definition-of-ready.md` — the `draft → ready` gate
  fields (FR-013).
- `docs/contracts/definition-of-done.md` — the
  `in_progress → verified` and `ratified → done` evidence/attestation
  requirements (FR-014).

## States (FR-013a)

`draft`, `ready`, `in_progress`, `verified`, `ratified`, `done`.

## Transition gates

| From          | To              | Gate |
|---------------|-----------------|------|
| `draft`       | `ready`         | DoR: `scope`, `acceptance_criteria`, `verification` non-empty (FR-013) |
| `ready`       | `in_progress`   | Authority matrix permits the actor to take the work (FR-015) |
| `in_progress` | `verified`      | Author records `verification.evidence_refs[]`; author ≠ ratifier (FR-007/FR-014) |
| `verified`    | `ratified`      | Ratification Record exists; ratifier ≠ author; surface valid; for FR-008 classes ratifier is human |
| `ratified`    | `done`          | Pre-merge attestation finalized with `merge_reference` after merge |

## Forbidden transitions (validator errors)

- Any skipped state (e.g. `draft → in_progress`).
- Any backflow (e.g. `done → ratified`).
- Any author-equals-ratifier crossing of the `verified → ratified`
  gate (FR-007).

## Validator checks

- `lifecycle.py`: derives the historical status sequence from git log
  on the spec sidecar (no external state) and asserts each transition
  satisfied its gate. Out-of-order transitions are surfaced with the
  offending FR cited (FR-027a, FR-027).
- `definition_of_ready.py`: `draft → ready` gate.
- `definition_of_done.py`: `in_progress → verified` evidence rule
  (rejects self-claims, FR-014); `ratified → done` attestation rule.

## Acceptance evidence

- examples/malformed/lifecycle-skipped-state.yml (FR-029) is rejected
  with a citation to FR-013a.
- examples/well-formed walks the full `draft → done` sequence.

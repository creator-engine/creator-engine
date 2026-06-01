# ADR-V2-007: Extension + hook contract substrate

## Status

Accepted for G2.006.0 draft substrate.

## Context

CE's hook machinery exists today as prose contracts (`CLAUDE_CODE_HOOK_PACK.md`,
`CLAUDE_CODE_CONTROLLER_SEAT_CONTRACT.md`), shell wrappers (`.claude/hooks/**`), and the
Ring 2 `hook_check.py` decision bridge — the three-ring model (Ring 0 HARD kernel,
Ring 1 RUNTIME/DEFEASIBLE hook-pack, Ring 2 VALIDATOR). There is no **declarative,
validatable schema** for an extension or its hooks, so the model's core safety property
(Ring 1 is defeasible; the HARD floor is Ring 0) lives only in prose. G2.006.0 is the
dependency floor for `G2.007.0` (harness seat-contract + hook-pack template) and must
formalize that shape without disturbing the running machinery.

## Decision

G2.006.0 adds `schemas/extension-hook-contract.schema.yaml` and the
`extension_hook_contract` validator check (registered via `checks/__init__.py`), with
examples, a prose contract, spec, and this ADR.

Key boundary decisions:

- **Shape-only substrate.** Schema + validator + examples + docs only. No runtime, no
  `ce` command, and **no modification** of the live hook-pack (`.claude/**`,
  `.claude/settings.json`) or the Ring 2 `hook_check.py` — those are the reference
  implementation, which a valid example must be able to *describe*.
- **Single combined record.** One `extension_contract` record carries the extension
  metadata (id, kind, ring, enforcement_strength) plus an embedded `hooks[]` array,
  rather than two separate record families — tighter and sufficient for the contract.
- **The three-ring coherence invariant is the substance.** A flat schema bounds the
  enums; the validator enforces the cross-field invariant a schema cannot express:
  `enforcement_strength: hard` is valid only at `ring_0`; a `ring_1` extension must be
  defeasible and its in-band hooks must fail open. This makes the model's safety
  property machine-checkable (`VAL-EXT-RING-COHERENCE`).
- **Provider/vendor-neutral, no secrets.** Contracts reference validators/credentials by
  name only; any inline secret value or inline Markdown metadata is rejected. Canonical
  non-ratifying roles only; `agent_ratifier`/`source` reserved-inactive.
- **Controller-decidable class (OD-16).** The contract shape is Controller-decidable
  (non-privileged `governance`); execution still proceeds under an Operator-ratified
  prompt, and review/merge remain separate ratified batches (review in a distinct
  CE-governed reviewer venue).

## Consequences

- The extension/hook contract is declarative and validatable, with the three-ring safety
  property enforced, on a stable substrate that `G2.007.0` (seat-contract + hook-pack
  template) builds on.
- The committed hook-pack remains the untouched reference implementation; later work can
  emit a contract record describing it and validate harness seats against it.

## Non-ratification statement

This ADR records a design decision for the PR candidate. It ratifies no runtime, no
modification of the live hook-pack/settings, no privileged-floor relaxation, and no
agent ratification.

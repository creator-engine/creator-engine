# Deferred-work ledger

## Purpose

The deferred-work ledger is the tracked, machine-readable source of residue
that an agent can resolve: findings deferred during review and work deliberately
split into later bundles. It is not an awaiting-operator list. Human decisions
belong to the human-decision process and use the `human` triage state only when
the residue cannot proceed without that decision.

The ledger is `.ce/deferred/ledger.yaml` and validates against
`schemas/deferred-work-ledger.schema.yaml` through the registered
`deferred_work_ledger` check.

## Record contract

Each entry has a stable `id`, a concise `summary`, provenance from a `review`,
`pull-request`, or `seal`, and a `scope_ref` into `vision.md`. The scope pointer
is the in-scope/out-of-scope oracle; an entry does not itself authorize work.

Each entry must be triaged into exactly one of:

- `already-resolved` — the cited residue is no longer actionable.
- `buildable-bundle` — a bounded, agent-resolvable next unit.
- `blocked` — an external technical dependency prevents the next unit.
- `human` — an operator decision is needed before work can proceed.

The ledger retains `created_at`, `triaged_at`, and `last_read_at` timestamps
plus a non-empty `read_back_marker`. `read_back_max_age_days` is a tracked
schema field. An entry becomes invalid when its age since `last_read_at`
exceeds that budget. This is a read-back ratchet: a ledger must feed attention
back into the work system instead of becoming a write-only archive.

The check also rejects `last_read_at` before `created_at`, and timestamps more
than 300 seconds ahead of the check clock. The small named skew allowance
accommodates controller handoffs without letting a far-future timestamp silence
the ratchet indefinitely.

## Belt source design

During pickup, a controller reads current `buildable-bundle` entries and uses
their provenance and `vision.md` scope pointer to form bounded candidate work.
The existing `forge/integrator_belt.py` substrate is the future re-feed seam;
this slice intentionally adds no belt code or actuator. The ledger is evidence
and intake material, never authority to launch work.

Triage quality remains a qualified input until the P1 real-embeddings brain
lane lands. Until then, the mechanical contract guarantees freshness and
provenance, not semantic completeness of the triage.

## Updating

When an entry is examined, update `last_read_at` and `read_back_marker`, then
re-triage it if its state changed. Schema-invalid writes fail closed; stale
entries fail the registered validator check.

## Residual boundary

The validator prevents only structurally impossible or far-future timestamp
abuse. A temporally plausible but false read-back marker remains subject to
source-control review and provenance scrutiny; the ledger does not grant
authority or establish the semantic truth of a triage decision.

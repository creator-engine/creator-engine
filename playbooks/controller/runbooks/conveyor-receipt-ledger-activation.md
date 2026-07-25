# Conveyor Receipt Ledger Activation

Use this procedure before restarting an armed conveyor daemon that has refused
an old unversioned `processed` receipt ledger. The normal daemon refusal is
intentional and remains in force; this is an explicit Operator migration, not a
startup repair.

## Safety boundary

The activation command is separate from daemon discovery. `plan` is read-only.
`apply` requires the exact reviewed plan digest, makes a durable private backup,
and converts each legacy handled tuple into a sealed terminal receipt. A sealed
receipt is discoverable for audit but cannot be claimed, which preserves the
no-re-entry guarantee for already handled terminal signals.

Do not use this procedure for a malformed, symlinked, public, or changed ledger.
Those conditions remain fail-closed. Do not remove or overwrite the file by
hand. The command verifies private descriptor-bound paths, file identity, and
directory durability before it changes state.

## Plan, review, then apply

Stop the daemon first and use its configured receipt-state path. Run the
activation module with the validator environment rather than bare Python.

```bash
state_path="/absolute/private/path/processed.json"
PYTHONPATH=validators python -m creator_engine_validator.conveyor_receipt_activation "$state_path" plan
```

Review the reported `plan_sha256` and receipt count. The command does not print
legacy receipt tuples or payload content. If the plan is accepted, apply only
that digest:

```bash
PYTHONPATH=validators python -m creator_engine_validator.conveyor_receipt_activation \
  "$state_path" apply --accept-plan-sha '<reviewed-plan-sha256>'
```

The operation refuses if the ledger inode or bytes changed after planning. On
success, verify the daemon still refuses any unsafe state, then restart through
the canonical launcher. A previously handled signal must be visible only as a
sealed terminal receipt and `claim()` must return false.

## Verified rollback

Rollback is also explicit and requires the reviewed activation plan digest. It
atomically restores the private durable legacy backup; normal discovery will
again refuse the unversioned state, rather than silently process it.

```bash
PYTHONPATH=validators python -m creator_engine_validator.conveyor_receipt_activation \
  "$state_path" rollback --accept-plan-sha '<reviewed-plan-sha256>'
```

If any command refuses, stop. Preserve the error and ledger metadata for review;
do not retry by deleting a ledger or backup.

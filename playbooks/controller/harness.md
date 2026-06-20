# Harness

## Runtime Contract

- Controller dispatch writes a governed-seat brief and visible work claim.
- Merge-gate requires independent review, green validation, and ratification.
- Seat-refresh follows the dev-3 pattern: save state, clear context, and resume
  from a precise state file.
- Courier-forge-op follows ADR-0007 model-b until the egress gateway lands.

## Courier-Forge-Op

The contained seat drafts the forge operation and signals it. An uncontained
courier executes that operation as the seat identity via the held token. The
courier does not author the operation or substitute its own identity.

## Halt Conditions

- No independent review for merge.
- Required checks are red, pending, or absent.
- Ratification is missing for merge or privileged operation.
- Courier cannot execute as the seat identity.

## Sunset

`courier-forge-op` sunsets when the ADR-0007 egress gateway / publish broker
lands and can carry the operation directly.

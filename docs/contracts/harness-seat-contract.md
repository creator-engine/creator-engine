# Harness Seat Contract

The harness seat contract is the tracked schema and validator layer for governed
Controller-seat launch posture. It is shape-and-validation only: it does not spawn
workers, mutate harness runtime files, or carry secrets.

## Foreman Dispatch

Every governed `seat_contract` must include `foreman_dispatch`:

- `launch_pinned: true`
- a non-empty `contract_ref`
- `roles.researcher`, `roles.implementer`, and `roles.reviewer`
- each role declares a non-empty `dispatch_capability`
- each role declares at least one non-empty `dispatch_surface`

Missing, incomplete, or unpinned foreman dispatch is invalid and is reported by
`harness_seat_contract` as `VAL-SEAT-FOREMAN-DISPATCH`.

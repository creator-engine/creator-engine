CE-410 slice 3 hardens Integrator live repair workspace allocation.

- Replaced predictable `--work-root` repair paths with daemon allocator-issued randomized workspaces.
- Added fail-closed `--runtime-root` queue-poll wiring and explicit `--work-root` refusal.
- Added offline coverage for allocator-backed workspaces, receipt cleanup, and unsafe runtime roots.

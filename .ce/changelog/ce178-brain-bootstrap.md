# ce-ops#178 - Brain Bootstrap

- Added a deterministic `ce brain bootstrap` payload for controller/foreman
  startup.
- The bootstrap path validates the Knowledge-SSOT assertion ledger before
  surfacing active scope-relevant assertions and fails closed on tampered or
  missing ledgers.
- Reuses the seat-class spine by resolving absent or unknown seat classes to
  `foreman`.
- Wires the bootstrap payload into real controller and lane launch paths before
  spawn side effects, exporting a value-free payload ref and SHA into the seat
  sentinel wrapper.

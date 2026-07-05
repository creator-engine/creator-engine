## ce-411 brain drift tombstone invariants

- **Declared work class:** S

- Hardened `ce brain verify --drift` with duplicate assertion ID tombstone invariants.
- Added drift-local errors for duplicate active IDs, invalid `superseded_by` chains, and tombstones ordered before the records they close.
- Covered invalid duplicate/tombstone shapes and a valid chained-supersede fixture in unit tests.

# ce-ops#166 - Knowledge SSOT Slice 2

- Added a versioned authoritative brain assertion ledger at
  `.ce/brain/assertions.yaml` for fleet-wide Knowledge-SSOT propagation.
- Synced the authoritative ledger into local `.ce/state` during bootstrap so the
  next launch picks up corrected shared assertions deterministically.
- Hardened brain drift checks to report stale loaded runtime ledgers when they
  diverge from the authoritative store.
- Seeded bounded shared capability and convention assertions with probe/static
  verification and unit coverage.

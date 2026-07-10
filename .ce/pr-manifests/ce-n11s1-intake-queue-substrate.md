# PR path manifest — N-11 slice 1 intake queue claim lifecycle

- **Declared work class:** M

Per-file purpose (closed path-set — 5 paths; carrier is self-inclusive):

- **`.ce/changelog/ce-n11s1-intake-queue-substrate.md`** *(A)* — per-PR changelog entry.
- **`.ce/pr-manifests/ce-n11s1-intake-queue-substrate.md`** *(A)* — this carrier.
- **`docs/design/conveyor-intake-queue.md`** *(M)* — queue lifecycle and ledger protocol.
- **`validators/creator_engine_validator/conveyor_intake_queue.py`** *(M)* — atomic queue claim lifecycle and append-only ledger.
- **`validators/tests/unit/test_conveyor_intake_queue.py`** *(M)* — lifecycle, race, stale-reclaim, and ledger coverage.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=1cb3f7987d8f71f626c87f1a1506c0bdc0fc776457dcd1b376b038d65b5583de

```text
.ce/changelog/ce-n11s1-intake-queue-substrate.md
.ce/pr-manifests/ce-n11s1-intake-queue-substrate.md
docs/design/conveyor-intake-queue.md
validators/creator_engine_validator/conveyor_intake_queue.py
validators/tests/unit/test_conveyor_intake_queue.py
```

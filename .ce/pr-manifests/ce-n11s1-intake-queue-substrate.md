# PR path manifest — N-11 slice 1 intake queue claim lifecycle

- **Declared work class:** M

Per-file purpose (closed path-set — 7 paths; carrier is self-inclusive):

- **`.ce/changelog/ce-n11s1-intake-queue-substrate.md`** *(A)* — per-PR changelog entry.
- **`.ce/pr-manifests/ce-n11s1-intake-queue-substrate.md`** *(A)* — this carrier.
- **`docs/design/conveyor-intake-queue.md`** *(M)* — queue lifecycle and ledger protocol.
- **`validators/creator_engine_validator/conveyor_intake_queue.py`** *(M)* — atomic queue claim lifecycle and append-only ledger.
- **`validators/tests/unit/test_conveyor_intake_queue.py`** *(M)* — lifecycle, race, stale-reclaim, and ledger coverage.
- **`validators/creator_engine_validator/conveyor_seat_pull.py`** *(A)* — verified injected seat-pull handoff adapter.
- **`validators/tests/unit/test_conveyor_seat_pull.py`** *(A)* — adapter verification, refusal, retry, and race coverage.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=61dbc33430cca17bc1f1401e0463eeca258316adc321b088a7d5b99fc46392c9

```text
.ce/changelog/ce-n11s1-intake-queue-substrate.md
.ce/pr-manifests/ce-n11s1-intake-queue-substrate.md
docs/design/conveyor-intake-queue.md
validators/creator_engine_validator/conveyor_intake_queue.py
validators/creator_engine_validator/conveyor_seat_pull.py
validators/tests/unit/test_conveyor_intake_queue.py
validators/tests/unit/test_conveyor_seat_pull.py
```

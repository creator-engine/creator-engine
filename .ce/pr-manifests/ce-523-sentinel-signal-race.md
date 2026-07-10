# PR path manifest - ce-523-sentinel-signal-race

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) for the closed authorized
path-set. CI runs `verify-path-manifest --base <PR base sha> --manifest-dir
.ce/pr-manifests --head-ref ce-523-sentinel-signal-race` and requires this
PR's `base..HEAD` diff to equal exactly the authorized paths below; this carrier
lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

Ratified scope:
Fix the intermittent xdist timing race in
`validators/tests/unit/test_seat_sentinel.py::test_wrapper_trapped_signal_writes_exit[1-129]`.
The wrapper process can return before the test's immediate JSONL read observes
the trapped-signal `exited` record on a loaded runner. This change keeps the
same exit-code contract and waits only for the durable evidence artifact the
product depends on for harvest.

Per-file purpose:
- `.ce/changelog/ce-523-sentinel-signal-race.md` - changelog fragment.
- `.ce/pr-manifests/ce-523-sentinel-signal-race.md` - this path carrier.
- `validators/tests/unit/test_seat_sentinel.py` - deterministic wait for the
  trapped-signal exit record before asserting it.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=9b28a5bee85d90381ef4ca70ede306662b972b49ba45b57d52f87d90fff4f768

```text
.ce/changelog/ce-523-sentinel-signal-race.md
.ce/pr-manifests/ce-523-sentinel-signal-race.md
validators/tests/unit/test_seat_sentinel.py
```

# PR path manifest - ce209-deflake-seat-sentinel

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce209-deflake-seat-sentinel

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
Controller relay for ce-ops#209 on 2026-06-23: de-flake the seat-sentinel
wrapper test that intermittently stalls the merge queue. The required
`Validate governance artifacts` gate runs ~4276 tests under pytest-xdist; on the
merge_group runner CPU contention makes one test exceed a tight fixed
wall-clock bound, failing the merge_group check and silently stalling the PR in
the queue. Fix the timing to be deterministic — poll for the expected condition
up to a generous ceiling — without weakening any assertion. No CI auto-retry
shim in this PR.

The changes:
- `validators/tests/unit/test_seat_sentinel.py`:
  `test_wrapper_trapped_signal_writes_exit[*]` replaced its tight 10s
  `deadline = time.time() + 10` busy-wait and `proc.wait(timeout=10)` with a
  generous 60s ceiling (`_WRAPPER_CEILING_S`) via a small `_poll_until` helper
  that polls every 50ms for the wrapper's launched line, and bounds `proc.wait`
  by the same ceiling. The test still asserts the trapped signal yields the
  correct exit code (SIGTERM->143, SIGHUP->129); only the timing is hardened. A
  genuinely hung process still fails at the ceiling.

Test-only change: no `_versions.py` bump, no new `ce` CLI group, no validator
wheel rebuild.

Per-file purpose (the closed path-set - 3 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce209-deflake-seat-sentinel.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce209-deflake-seat-sentinel.md`** *(A)* - this carrier.
- **`validators/tests/unit/test_seat_sentinel.py`** *(M)* - deterministic
  poll-with-ceiling de-flake of the trapped-signal wrapper test.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=5ac4123f89c9588d075484bf3aa1885a49389bfa7046f59c04d71590fdac31a5

```text
.ce/changelog/ce209-deflake-seat-sentinel.md
.ce/pr-manifests/ce209-deflake-seat-sentinel.md
validators/tests/unit/test_seat_sentinel.py
```

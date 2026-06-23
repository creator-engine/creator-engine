---
slug: ce209-deflake-seat-sentinel
date: 2026-06-23
kind: fixed
scope: seat-sentinel wrapper test timing
issue: ce-ops#209
---

De-flaked the seat-sentinel wrapper test that intermittently stalled the merge
queue. `test_wrapper_trapped_signal_writes_exit` relied on a tight fixed 10s
wall-clock bound (`deadline = time.time() + 10` for the launched line and
`proc.wait(timeout=10)` for exit); under pytest-xdist load on the contended
merge_group runner the wrapped subprocess legitimately needed longer, the hard
`subprocess.TimeoutExpired` fired, and the failed merge_group check silently
stalled the PR in the queue.

The wait is now deterministic: a small `_poll_until` helper polls every 50ms for
the expected condition (the wrapper writing its launched line) up to a generous
60s ceiling that is not reached in practice but tolerates a slow loaded runner,
and `proc.wait` is bounded by the same ceiling so a genuinely hung process still
fails. The assertion is unchanged — the trapped signal still must yield the
correct exit code (SIGTERM->143, SIGHUP->129); only the timing was hardened.

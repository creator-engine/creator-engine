# DISPATCH — dev-4 — 2026-07-10 — unit: sentinel signal-race flake fix — class S
Role: implementer foreman. Signal: `READY-FOR-HARVEST ce-523-sentinel-signal-race <full-40-hex-sha>`
or `BLOCKED ce-523-sentinel-signal-race <one-line-reason>`.
Branch `ce-523-sentinel-signal-race` off freshly fetched origin/main; worktree /var/tmp/wt-<branch>.

## Problem (embedded; observed live 2026-07-10 on a host preflight baseline run)
`validators/tests/unit/test_seat_sentinel.py::test_wrapper_trapped_signal_writes_exit[1-129]`
fails intermittently under xdist (-n auto): a clean origin/main baseline failed it while
adjacent runs passed. Class: signal-delivery timing race under parallel worker load (the
wrapper receives/traps a signal and must write its exit record; the test races the write).
Cost: preflight noise + false-RED risk on unrelated PRs.

## Unit
1. Reproduce under stress (run the single test repeatedly under -n auto alongside a busy
   worker set, or loop it ~50x) to confirm the race window.
2. Smallest-good fix in the TEST unless the wrapper itself has a real durability bug:
   deterministic wait for the exit-record write (poll-with-deadline on the record path)
   instead of a fixed-order assumption. If your diagnosis shows the WRAPPER can genuinely
   lose the write on signal (a product bug, not a test race), STOP at diagnosis and signal
   BLOCKED with the evidence — that variant is a different work class.
3. Do NOT weaken the exit-code contract assertions; the fix makes the test deterministic,
   not lenient. No retry-until-pass loops around the whole test.
Files: validators/tests/unit/test_seat_sentinel.py (and ONLY if proven product bug: stop
instead), changelog `.ce/changelog/ce-523-sentinel-signal-race.md`, carrier (slug=branch)
with exactly `- **Declared work class:** S`. Product lens in prose.

## Stop lines
Everything else — especially the sentinel wrapper production code (diagnosis-stop rule above),
launch_runtime.py, seat_reaper.py, doctor_runtime.py, checks/**, forge/**, deploy/**,
.github/**, .ce/brain/assertions.yaml. Focused tests only; commit before signal.

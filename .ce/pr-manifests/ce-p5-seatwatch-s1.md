# PR path manifest — ce-p5-seatwatch-s1 · seat-watch daemon slice 1

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the path manifest convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-p5-seatwatch-s1
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below.

Base:
`402192ddc921a4eb0c439ee5c7eb9b1304dcb9bd` (`origin/main`, worktree creation base).

Summary:
- **Declared work class:** feature
- Adds the observe-only seat-watch daemon core and environment runner.
- Adds systemd and launcher deployment artifacts under `deploy/seat-watch/`.
- Adds focused unit coverage for event emission, pane error classification, idle tracking, dispatch acknowledgements, config parsing, and multi-seat state isolation.
- Adds the slice 1 design note and changelog fragment.

Per-file purpose (the closed path-set — 8 paths):
- **`.ce/changelog/ce-p5-seatwatch-s1.md`** *(A)* — changelog fragment.
- **`.ce/pr-manifests/ce-p5-seatwatch-s1.md`** *(A)* — this carrier.
- **`deploy/seat-watch/DESIGN.md`** *(A)* — observe-only daemon design, event schema, config reference, and slice 2 roadmap.
- **`deploy/seat-watch/ce-seat-watch.service`** *(A)* — systemd unit for the observe-only daemon.
- **`deploy/seat-watch/launch-seat-watch.sh`** *(A)* — launcher with health and one-shot modes.
- **`validators/creator_engine_validator/seat_watch_daemon.py`** *(A)* — polling logic, event emission, idle tracking, pane error classification, BLOCKED parsing, and dispatch ack detection.
- **`validators/creator_engine_validator/seat_watch_runner.py`** *(A)* — env config loading, singleton lease wiring, signal handling, and JSONL event writes.
- **`validators/tests/unit/test_seat_watch_daemon.py`** *(A)* — focused daemon and config tests.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=3e3daa67fa7562a257e7e8582795da88b360ad22b4d821dd8ec224ad18cafc0c

```text
.ce/changelog/ce-p5-seatwatch-s1.md
.ce/pr-manifests/ce-p5-seatwatch-s1.md
deploy/seat-watch/DESIGN.md
deploy/seat-watch/ce-seat-watch.service
deploy/seat-watch/launch-seat-watch.sh
validators/creator_engine_validator/seat_watch_daemon.py
validators/creator_engine_validator/seat_watch_runner.py
validators/tests/unit/test_seat_watch_daemon.py
```

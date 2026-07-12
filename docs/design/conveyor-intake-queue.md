# Conveyor Intake Queue

The conveyor intake queue is a local, file-backed list of controller-declared ticket units. It lives by default under `.ce/state/conveyor-daemon/intake-queue/`, or under `CE_CONVEYOR_INTAKE_QUEUE_ROOT` when configured. Its state directories are `pending/`, `claimed/`, and `done/`; lower numeric priorities sort first in filenames of the form `{priority:05d}-{unit_id}.yaml`.

Each unit pins its dispatch brief with `brief_ref` and a 40- or 64-hex lowercase `brief_sha`, and declares its allowed `territory_paths`. These values are value-free metadata: no tokens or credentials are stored in a unit, and a queue claim grants no authority beyond that already held by the claimer.

`stock` (also `publish_entry`) puts a unit in `pending/`. `claim_entry(claimer, ttl_seconds=...)` moves it to `claimed/` and records `claimed_by`, `claimed_at`, and optional `claim_expires_at`; legacy `claim_next()` remains available as a no-expiry controller claim. `release_entry` returns an owned claim to `pending/` and clears those fields. `complete_entry` requires the owning claimer and moves the entry to `done/`; legacy `mark_done` remains its no-claimer compatibility wrapper.

Before claiming pending work, the queue scans `claimed/` for expired claims. It clears their claim fields, atomically returns them to `pending/`, and records a stale reclaim. The move from `pending/` to `claimed/` uses POSIX `os.replace`, so concurrent claimers have exactly one winner; a losing rename observes `FileNotFoundError` and continues scanning.

Every claim, release, completion, and stale reclaim best-effort appends an NDJSON record to `intake-claims.jsonl` at the queue root. Records include `action`, `unit_id`, `claimer`, `brief_sha`, and `ts`. Ledger I/O failure is reported to stderr but never aborts the associated lifecycle operation; the ledger is append-only and is never truncated.

The feature remains gated by `CE_CONVEYOR_INTAKE_ENABLED=1`; absent that flag, daemon behavior is unchanged. This queue substrate does not send pane text, write sockets, launch seat subprocesses, or grant any new authority.

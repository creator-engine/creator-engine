# DISPATCH — dev-4 — 2026-07-10 — unit: N-11 slice 1 intake queue substrate — class M

PRIOR IMPLEMENTATION FOUND ON MAIN — read before writing any code.

`validators/creator_engine_validator/conveyor_intake_queue.py` already ships the local
file-backed queue (`IntakeQueue`, `IntakeUnit`, `IntakeQueueReader`,
`stock`/`claim_next`/`list_pending`/`mark_done`). `docs/design/conveyor-intake-queue.md`
explicitly defers "live dispatch, claiming, and seat handoff" to slice 2. Tests exist at
`validators/tests/unit/test_conveyor_intake_queue.py`. `conveyor_daemon_runner.py` has
`CE_CONVEYOR_INTAKE_ENABLED` and `intake_queue_root` already wired. This brief scopes the
GENUINE GAP: dispatch-doctrine fields (`brief_sha`, `territory_paths`), full claim lifecycle
(`claimed_by`, `claimed_at`, `claim_expires_at`, stale reclaim), `release_entry`, and an
NDJSON audit ledger.

Role: implementer foreman.
Signal (green): `READY-FOR-HARVEST ce-n11s1-intake-queue-substrate <full-40-hex-sha>`
Signal (blocked): `BLOCKED ce-n11s1-intake-queue-substrate <one-line reason>`
Branch: `ce-n11s1-intake-queue-substrate` off origin/main OR LATER.
Worktree: /var/tmp/wt-ce-n11s1-intake-queue-substrate
Standing preflight (ce-ops#303): `/workspace/creator-engine/.venv/bin/ce validate-pr
--profile contained-seat` before every commit-for-harvest. Do not discover gates via CI.
PRE-SIGNAL CHECKLIST: focused tests green + confidentiality check:
`python -m pytest validators/tests/unit/test_public_docs_confidentiality.py::test_tracked_text_files_contain_no_new_confidential_or_internal_references -q`
must PASS before the READY signal is sent.

## Context

Verified paths on origin/main:
- `validators/creator_engine_validator/conveyor_intake_queue.py` — existing queue. `IntakeUnit`
  fields today: `unit_id`, `brief_ref` (path string only — no sha), `branch`, `worktree`,
  `priority`, `work_class`, `status` (`pending|claimed|done`), `created_at`. Missing:
  `brief_sha`, `territory_paths`, `claimed_by`, `claimed_at`, `claim_expires_at`. No
  `release_entry`. No claim ledger.
- `validators/tests/unit/test_conveyor_intake_queue.py` — existing tests (stock, claim_next,
  mark_done, reader, config). Missing: release, stale-reclaim, race, ledger.
- `docs/design/conveyor-intake-queue.md` — design doc; its deferral sentence for "Live
  dispatch, claiming, and seat handoff" is what this slice fulfills.
- `validators/creator_engine_validator/forge/resource_lock.py` — `os.O_CREAT|os.O_EXCL` +
  `_reclaim_guard` idiom for stale-expiry reclaim; mirror for claim TTL.
- NDJSON ledger idiom: `json.dumps(record, sort_keys=True) + "\n"`, open `"a"` mode,
  injectable clock returning RFC 3339 UTC `Z` (same pattern as the in-flight review-acting
  module — copy the PATTERN as your own implementation; do NOT import from other worktrees).
- `tools/egress-broker/egress_broker/policy.py` — contained-seat egress is broker-mediated;
  the queue is LOCAL-FILESYSTEM (launcher mounts the queue root via
  `CE_CONVEYOR_INTAKE_QUEUE_ROOT`); no new egress authority needed or granted.

Atomic-claim mechanism choice: local filesystem `os.replace` (pending/ → claimed/ rename).
POSIX-atomic; the concurrent loser gets FileNotFoundError on the renamed source and falls
through to the next entry. git-CAS rejected for this slice (network round-trips + distributed
consensus out of scope). State this choice in a module-level docstring note.

## Unit

U1 — Extend `conveyor_intake_queue.py` (do NOT remove or rename existing public API):

Schema additions to `IntakeUnit` (keep all existing fields):
- `brief_sha: str` — 40- or 64-hex sha pinning the brief at dispatch time (pointer+sha
  doctrine); validated `[0-9a-f]{40}` or `[0-9a-f]{64}` on read; reject empty.
- `territory_paths: tuple[str, ...]` — controller-declared path territory; may be empty.
- `claimed_by: str | None = None`, `claimed_at: str | None = None` (ISO-8601 UTC),
  `claim_expires_at: str | None = None` (None = no expiry).

Methods on `IntakeQueue`:
- `publish_entry(unit)` — alias for `stock` (keep `stock`).
- `list_open(*, read_error_sink=None)` — alias for `list_pending` (keep `list_pending`).
- `claim_entry(claimer, *, ttl_seconds=None, clock=None) -> IntakeUnit | None` — first scan
  `claimed/` for expired `claim_expires_at` (injected clock), rename stale entries back to
  `pending/` + append `stale_reclaim` ledger record. Then iterate `pending/` sorted; attempt
  `os.replace`; on FileNotFoundError skip to next (concurrent claimer won). On success write
  updated unit atomically (claimed_by/claimed_at/claim_expires_at) + append `claimed` ledger
  record. Keep `claim_next()` as a zero-arg backward-compatible wrapper (claimer="controller",
  ttl None).
- `release_entry(unit_id, claimer, *, clock=None)` — claimed → pending with claim fields
  cleared; FileNotFoundError if not in claimed/; PermissionError on claimer mismatch; append
  `released` record.
- `complete_entry(unit_id, claimer, *, clock=None)` — ownership-checking `mark_done`;
  PermissionError on mismatch; append `completed` record. Keep `mark_done` as no-claimer
  wrapper.

NDJSON claim ledger at `<queue_root>/intake-claims.jsonl`: one record per event
`{"action": "claimed"|"released"|"completed"|"stale_reclaim", "unit_id", "claimer",
"brief_sha", "ts"}`. Append-only, never truncate. Ledger write is best-effort: on OSError log
to stderr and continue (ledger failure must never abort the claim operation).

Authority limit (state in docstring): units carry value-free data only (sha strings, paths);
no tokens, no credentials; claiming grants NO authority beyond what the seat already has.

U2 — Extend `test_conveyor_intake_queue.py` (add; do not remove existing tests):
brief_sha-required-nonempty; territory_paths roundtrip; claim sets fields; RACE two concurrent
claimers exactly-one-wins; release returns to pending; release wrong-claimer PermissionError;
stale claim reclaimed via advanced injected clock; complete wrong-claimer PermissionError;
ledger records full lifecycle (claimed/completed with correct unit_id+brief_sha);
stale_reclaim recorded in ledger.

U3 — Update `docs/design/conveyor-intake-queue.md`: remove the slice-2 deferral sentence;
document new fields, claim/release/complete lifecycle, ledger path, stale-reclaim protocol,
and the os.replace atomicity rationale.

## Files (allowed writes)

- validators/creator_engine_validator/conveyor_intake_queue.py (extend — preserve existing API)
- validators/tests/unit/test_conveyor_intake_queue.py (extend — preserve existing tests)
- docs/design/conveyor-intake-queue.md (update)
- .ce/changelog/ce-n11s1-intake-queue-substrate.md (new)
- .ce/pr-manifests/ce-n11s1-intake-queue-substrate.md (new carrier; exactly
  `- **Declared work class:** M`)

No other paths. Any write outside this list is a stop-line violation.

## Stop lines

No push, no PR, no signing, no approval/merge action. No daemon deployment, no systemd
changes, no new env-var gates beyond those already in conveyor_daemon_runner.py. No authority
expansion; no tokens/credentials in queue entries. `.github/**`, `checks/**`, `pr_preflight.py`
untouched. Do not modify conveyor_daemon_runner.py, review_acting.py, or any other in-flight
module; do not import from other worktrees. NDJSON ledger append-only. Do not implement the
arc-feed daemon, seat-side auto-pull loop, or pane-dispatch retirement — later slices.

## Signal

On green preflight: `READY-FOR-HARVEST ce-n11s1-intake-queue-substrate <full-40-hex-sha>`
On block: `BLOCKED ce-n11s1-intake-queue-substrate <one-line reason>`
Commit early and often.

PATH note: use absolute `/workspace/creator-engine/.venv/bin/ce` and
`/workspace/creator-engine/.venv/bin/python`; do not rely on PATH-resolved `ce`.

# Seat / Venue Retirement Reaper Protocol

The reaper mechanizes the manual seat/venue retirement runbook — *archive the
transcript → tear down the terminal venue → release the secondary worktree →
release the instance-local ledger markers* — so spent seats are retired within
minutes of their terminal event with **zero orchestrator involvement**.

It is triggered by the **terminal lifecycle facts** the seat sentinel
writes to each seat's append-only `events.jsonl`, never by orchestrator memory,
live pane discovery, or inferred scheduler intent.

Command surface (mirrors the `notify once|watch|status` I/O-edge daemon style):

```text
ce reap once      # one fold + one bounded action pass
ce reap watch     # repeat `once` at an interval (SIGINT/SIGTERM stop cleanly)
ce reap status    # a no-mutation read model (classification + counts)
```

## Architecture

| Layer | Module | Responsibility |
|-------|--------|----------------|
| Policy (substrate-neutral) | `seat_reaper.py` (V3) | fold local state, classify every seat, orchestrate the ordered pipeline, emit escalations, write the private reaper ledger, count honestly |
| Executor (per-substrate) | `reaper_executors.py` (V3) | irreversible venue actions — tmux today; an unknown substrate yields no executor |
| CLI | `v3_cli.py` `reap once\|watch\|status` | thin wiring over the policy |

The **policy never shells out** to tmux, git, or a worker runtime. Every
irreversible action is delegated to an executor selected by the venue substrate.

### Version boundary (§3.6)

`seat_reaper` and `reaper_executors` are `V3_RUNTIME`. They import **no**
`V1_RUNTIME` module. The two crossings to v1 surfaces are **subprocess + DATA**:

- transcript archive → `ce lane archive --transcript … --archive-root …
  --batch-slug … --role … --repo-root … --json` (consume only the JSON
  `archive_path` + `sha256`, then re-verify the bytes);
- worktree/claim/lease release → `creator-engine-validator pco-release --lane-id …
  --controller-id … --ledger-root … --repo-root … --release-reason …` (then
  verify the claim/lease/event/worktree facts off disk).

The seat sentinel (`seat_sentinel.py`) is *shared*-classified, so the reaper reads
its tolerant event readers + contract constants as DATA. The reaper **re-implements
the outcome resolution READ-ONLY** (`resolve_outcome_readonly`) and **never calls
`seat_sentinel.resolve_outcome()`**, which appends an `outcome_resolved` event and
would forge writer-provenance + mutate the trigger surface on every pass.

## Read-only discipline

`ce reap status`, and the **evaluation phase** of `once`/`watch`, write nothing:
no `events.jsonl` append, no dispatch / escalation / reaper-ledger / archive /
pane-registry write. `events.jsonl` is byte-identical before and after any
evaluation pass that does not retire.

## Classification (deterministic)

Every observed seat ends in exactly one bucket. Re-running `status` over unchanged
state yields identical classifications and counts.

| Classification | Trigger |
|----------------|---------|
| `eligible` | launched **and** exited, terminal-clean, resolvable-or-within-grace, no conserve marker |
| `archive_then_retire` | failed/refused spawn (`spawn_failed_at`) with no conserve marker — evidence is archived, venue closed, but the dispatch/evidence are never destroyed |
| `conserved` | `conserve: true` on the dispatch — an **absolute stop**: no teardown of any kind |
| `escalate_unclean_stop` | launched but no exit (dead pid / missing events / killed wrapper) |
| `escalate_unresolved_outcome` | exited, but the outcome stays unresolvable past the staleness grace window |
| `escalate_missing_archive` | archive required for retirement could not be produced |
| `escalate_unknown_executor` | the venue substrate has no safe executor |
| `active_or_unknown` | not terminal and not stale enough to escalate (still running / in-flight) |
| `already_retired` | the reaper ledger shows a verified prior retirement |
| `failed` | an attempted step failed after a previous step succeeded |

Staleness is **advisory** — a stale or dangling-`launched` seat **escalates**; it is
never auto-killed. This composes with the dangling-launched reconciler;
the reaper uses the same classification facts but does not supersede its authority.

## Retirement pipeline (ordered, verified)

For an `eligible` / `archive_then_retire` seat, the policy runs an ordered
pipeline; a later step never runs unless the earlier step verified:

1. **Archive evidence** — *before any venue or worktree mutation.* The executor
   archives via `ce lane archive --json`; the policy then verifies the archive file
   exists, re-hashes it against the reported SHA-256, and confirms the dispatch /
   runtime-evidence files still exist. A required-but-missing archive → escalate.
2. **Close the terminal venue** — kill only the seat's pane, verify the pane is
   absent, and mark the pane-registry record `closed`/`completed` (clean) or
   `aborted`/`aborted` (archive-then-retire). A pane-registry write failure stops
   the pipeline before worktree release.
3. **Release the worktree + ledger markers** — via the existing `pco-release` leg
   (release reason `completed` for a clean terminal, `aborted` for a failed/refused
   dispatch). The policy verifies the claim is released, the lease is gone, a
   `claim_released` event exists, and the worktree was removed — **without** branch
   deletion or any GitHub mutation.
4. **Record retirement** — append one entry to the private NDJSON ledger
   `<state_root>/reaper/ledger.ndjson` only after every required step verified. The
   dispatch record and sentinel events remain preserved.

`pco-release` remains the **only** worktree/claim/lease release leg. Running `once`
twice never double-kills a pane, double-appends a release, or inflates `reaped`.

## Escalations

The reaper emits **normal escalation records** into the existing queue
(`<state_root>/escalations/<id>.yaml`, validated against
`escalation-record.schema.yaml`), so the B.8 notify feed banners them — there is no
private alert format. Escalation ids are deterministic
(`reaper-<reason>-<digest>`), so the same unresolved source/reason never opens a
duplicate.

## Conserved-evidence marker

A dispatch may carry the additive-optional marker (dispatch-record schema):

```yaml
conserve: true
conserve_reason: "<short operator or policy reason>"
conserved_at: "<RFC3339 timestamp>"
```

When present it is an **absolute** stop condition: no teardown, no `pco-release`,
no worktree removal, no pane kill, and no archive mutation.

## Honest counters

Counters describe what actually happened, not intent. `reap once` reports
`observed_dispatches`, `eligible`, `reaped`, `conserved`, `escalated`,
`skipped_active_or_unknown`, `already_retired`, `failed`, plus per-step
`step_counts` distinguishing `succeeded` / `already_satisfied` / `not_applicable` /
`failed`. A seat is **never** counted `reaped` for merely emitting an escalation,
merely archiving, or merely killing a pane.

## Rollback

Stop any `ce reap watch` process. Do **not** delete archives, dispatch records,
sentinel events, runtime evidence, or escalations created by prior runs. Rely on
`pco-release` idempotency for already-released seats. Resolve reaper-created
escalations only after human inspection. If archive succeeded but a later step
failed, the archive is preserved and the seat escalates; if `pco-release` completed
but the final ledger write failed, `status` verifies the underlying
claim/lease/worktree state and classifies `already_retired` rather than attempting a
second destructive pass.

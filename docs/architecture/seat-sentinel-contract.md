# Seat lifecycle sentinels — the push-not-poll observation contract (ce-ops#26)

Status: **LIVE** (ce-ops#26). Risk class: MEDIUM (v1 launch-path mutation,
additive wrap; instance-local gitignored state only).

## Why

Seat observation was tier-1 polling — `tmux capture-pane`, periodic
`gh pr list`, dispatch-record re-reads. A seat that **dies silently writes
nothing**, so silence looked like progress. ce-ops#26 standardizes a per-seat
sentinel surface: every `ce launch`-ed seat mechanically emits machine-watchable
lifecycle events — written by the **launcher's wrapper, never the seat's
model** — so (a) the orchestrator's Monitor blocks on a file event instead of
polling, (b) the cockpit L2 renders the same events through one contract, and
(c) every terminal state, **including abnormal death, is observable**.

## The contract (substrate-neutral)

Every launched seat owns an **append-only `events.jsonl`** at
`<state_root>/dispatches/<seat_id>/events.jsonl`. Each line is one versioned,
value-free JSON object conforming to `schemas/seat-event.schema.yaml`. The file
is append-only — one `write(2)` per line under `O_APPEND` (lines ≪ 4 KiB ⇒
atomic on POSIX); never rewritten or renamed, so `tail -f`/inotify semantics
hold.

### seat_id

- **Dispatch-driven seats** (`v3_seat_bridge.spawn_seat`): `seat_id = run_id`;
  events land NEXT TO `dispatch.yaml` — the directory IS the join, no new
  pointer field. The dispatch record also carries an optional `events_ref`.
- **v1-only launches** (`ce lane launch`): `seat_id = lane_id`.
- **Bare Controller seats** (`ce launch`, no dispatch): `seat_id =
  <session>--<window>` slug.

### Event line schema (v1)

| field | events | meaning |
|---|---|---|
| `v` | all | integer schema version (`1`), required day one |
| `event` | all | `launched` \| `exited` \| `outcome_resolved` (closed enum; `progress`/`heartbeat` reserved) |
| `ts` | all | UTC RFC3339, wrapper-observed |
| `seat_id` | all | the identity above |
| `run_id` | all | dispatch run_id when dispatch-driven, else `null` |
| `writer` | all | `launcher_wrapper` — the writer-role rule made data |
| `pid` | launched | the wrapper pid (the seat process-tree root) |
| `command_sha256` | launched | digest of the inner argv — **never the command text** (the ps-leak lesson) |
| `exit_code` | exited | mechanical truth, wrapper-observed (`137` = OOM-group SIGKILL) |
| `signal` | exited (optional) | readers MAY derive (`exit_code − 128`); the wrapper does not compute it |
| `outcome` | outcome_resolved | THE conserved run-OUTCOME enum (identical to `runtime-evidence.schema.yaml`), or `null` |
| `outcome_source` | outcome_resolved | `runtime_evidence` \| `unresolved` (honest-tiering) |
| `evidence_ref` | outcome_resolved | the chain document consulted, or `null` |

The `outcome` enum is **referenced**, not redeclared with drift — a unit test
pins it byte-identical to `runtime-evidence.schema.yaml`.

## The writer: a generated POSIX-sh supervisor

`creator_engine_validator.seat_sentinel.build_wrapper_script(...)` is **PURE**
(deterministic text; argv embedded via `shlex.quote`); the launcher writes it to
`<seat_dir>/sentinel-wrapper.sh` (0700) and the pane command becomes
`["/bin/sh", "<abs>/sentinel-wrapper.sh"]`. The wrapper:

1. appends `launched`;
2. runs the (already-governed, already-bounded) seat command as its
   **FOREGROUND** child — interactive tty preserved;
3. traps `HUP`/`TERM`/`INT` to write a trapped `exited` event;
4. on a normal return appends `exited` with the child's exit code;
5. best-effort shells out to the pinned interpreter for `outcome_resolved`
   (failure never masks the exit event or alters the exit code).

The seat's model never writes the file — **silence ≠ success**. POSIX sh only
(no bashisms), so the script is OS-neutral; the first watcher (`inotifywait`)
being Linux-only is an implementation note, not a contract term. A future
container seat sets `ENTRYPOINT ["/bin/sh", "sentinel-wrapper.sh"]` and emits
identical events; only the injection point (pane-command replacement) is
tmux-shaped, confined to the two launch modules.

## Ordering (load-bearing): the wrapper sits OUTSIDE the seat cgroup

Injection is **outermost** — applied to the OUTPUT of the v3.5-F bounding wrap
(`resource_bound_spec.build_bounded_command`), immediately before pane spawn. So
the wrapper sits OUTSIDE the `systemd-run --scope` seat cgroup: when the v3.5-F
`memory.oom.group=1` group-kill takes the seat scope, **the wrapper survives to
write `exited` (137)**. OOM death — the motivating crash class — is observable
by construction. The sentinel only OBSERVES; it never gates launch, and
launch-confirm (which RAISES on resource-scope failure) is unchanged.

## Consumers

- **Cockpit L2** (`runner/cockpit_readmodel.load_seat_events`): folded into
  `snapshot_from_roots` and joined to dispatch entries by `seat_id == run_id`.
  The file lives inside the subtree `watch_paths` already names, so the live
  tail (`watchfiles.awatch`, recursive) fires for free — **`watch_paths` gains
  nothing**. L2 stays a pure JSON read-model.
- **Orchestrator Monitor** (ops convention): `inotifywait -e modify
  <events.jsonl>` or `tail -n0 -f` blocks until the next line; completion = an
  `exited` line. Linux-only watcher tooling is fine — the CONTRACT is OS-neutral.

## What this is NOT (declared non-goals)

- **Not evidence-of-record.** The runtime-evidence chain remains authoritative;
  `events.jsonl` is observability. No hash-chaining/tamper-evidence in v1.
- **Spawn failures** raise BEFORE side effects, so no wrapper exists yet —
  `v3_seat_bridge.mark_spawn_failed` remains that surface; readers union the two.
  No event is invented for a seat that never had a process.
- **Residual** (§3.9): `SIGKILL` of the wrapper itself, tmux-server death, or
  host crash leaves a dangling `launched` with no `exited`. `launched.pid`
  enables reader-side staleness; a `ce seat reap` reconciler is future work. The
  contract is honest: absence of `exited` means **UNKNOWN-TERMINAL, never
  success** — still strictly better than today, where absence of everything
  means nothing.

# Seat-Watch Daemon Slice 1

## Purpose

The seat-watch daemon closes the controller awareness gap by polling configured
seat panes on a fixed interval and writing structured events to an append-only
JSONL feed. The feed lets controller-side tooling observe READY signals,
BLOCKED signals, unchanged idle panes, pane probe failures, and delivery
acknowledgements without requiring manual pane reads.

Slice 1 is observe-only. It reads pane text through configured probe argv,
emits JSONL events, and optionally mirrors those events to a second file for
webhook-style collection. It has no dispatch authority, does not write herd or
queue state, and does not read any intake queue. Later slices can consume the
event feed without changing the probe or event-emission core.

Each watched seat is configured as a `seat_id` plus an argv array. The daemon
reuses the existing conveyor probe machinery: `SeatProbeSpec`,
`subprocess_probe_runner`, and `parse_ready_for_harvest_signals`. This keeps
pane access semantics aligned with the existing conveyor discovery path and
avoids duplicating READY parsing rules.

## Event Schema

Every event is one JSON object per line. The primary feed path is
`CE_SEAT_WATCH_FEED_PATH`; if `CE_SEAT_WATCH_WEBHOOK_FILE` is set, the same
event line is also appended to that file.

Every event has these top-level fields:

```json
{
  "schema_version": "1",
  "event_type": "<type>",
  "seat_id": "<seat-id>",
  "ts": "2026-07-09T06:30:00Z",
  "poll_index": 42,
  "detail": {}
}
```

The timestamp is UTC ISO-8601 with a `Z` suffix. `poll_index` is zero-based
within the current daemon process.

### `ready_signal`

Emitted once for each parsed READY-FOR-HARVEST signal in the current pane text.
READY parsing is delegated to the conveyor discovery parser, including its
slug and SHA validation.

```json
{
  "schema_version": "1",
  "event_type": "ready_signal",
  "seat_id": "<seat-id>",
  "ts": "2026-07-09T06:30:00Z",
  "poll_index": 42,
  "detail": {
    "branch": "<branch-slug>",
    "sha": "<40-hex sha>",
    "tag": "<tag string or null>"
  }
}
```

### `blocked_signal`

Emitted once for each line matching `BLOCKED <branch> <reason>`.

```json
{
  "schema_version": "1",
  "event_type": "blocked_signal",
  "seat_id": "<seat-id>",
  "ts": "2026-07-09T06:30:00Z",
  "poll_index": 42,
  "detail": {
    "branch": "<branch-slug>",
    "reason": "<remainder of BLOCKED line after branch>"
  }
}
```

A READY or BLOCKED signal resets the unchanged-pane idle counter for that seat.

### `idle_without_signal`

Emitted when pane text remains unchanged for the configured threshold and the
current poll has no READY or BLOCKED signal.

```json
{
  "schema_version": "1",
  "event_type": "idle_without_signal",
  "seat_id": "<seat-id>",
  "ts": "2026-07-09T06:30:00Z",
  "poll_index": 42,
  "detail": {
    "polls_unchanged": 5,
    "pane_hash": "<sha256 hex digest of pane text>"
  }
}
```

After the event is emitted, the unchanged counter resets so another full
threshold window is required before a repeat event.

### `pane_error`

Emitted when a pane probe raises an exception. Probe errors are missing data:
they do not update the last pane hash or previous pane text for that seat.

```json
{
  "schema_version": "1",
  "event_type": "pane_error",
  "seat_id": "<seat-id>",
  "ts": "2026-07-09T06:30:00Z",
  "poll_index": 42,
  "detail": {
    "error_class": "limit|auth|exit_143|probe_failed|unknown",
    "detail": "<exception class name and message, first 400 chars>"
  }
}
```

Classification is applied in this order:

| Class | Condition |
| --- | --- |
| `exit_143` | subprocess probe exited with return code 143 |
| `limit` | exception text contains `rate limit`, `quota`, or `429` |
| `auth` | exception text contains `unauthorized`, `401`, or `authentication` |
| `probe_failed` | other subprocess or timeout failure |
| `unknown` | any other exception |

### `dispatch_delivery_ack`

Emitted when a configured pattern appears in pane text and was absent from the
previous successful pane text for the same seat. Matching is case-insensitive.

```json
{
  "schema_version": "1",
  "event_type": "dispatch_delivery_ack",
  "seat_id": "<seat-id>",
  "ts": "2026-07-09T06:30:00Z",
  "poll_index": 42,
  "detail": {
    "pattern_matched": "<configured pattern>",
    "context_line": "<first line containing the match, truncated at 200 chars>"
  }
}
```

The event is emitted once for each newly appearing pattern. If the same pattern
remains visible across later polls, no duplicate acknowledgement is emitted
until it disappears and appears again in a later successful probe result.

## Configuration

Required environment:

| Variable | Description |
| --- | --- |
| `CE_SEAT_WATCH_SEAT_PROBES` | JSON array of probe specs, for example `[{"seat_id":"<seat-id>","argv":["<probe-command>","<arg>"]}]`. |
| `CE_SEAT_WATCH_FEED_PATH` | Absolute path to the append-only JSONL event feed, such as `<feed-path>`. |
| `CE_DAEMON_LEASE_ROOT` | Singleton lease root directory, such as `<lease-root>`. |

Optional environment:

| Variable | Default | Description |
| --- | --- | --- |
| `CE_SEAT_WATCH_INTERVAL_SECONDS` | `30` | Poll interval in seconds; must be greater than zero. |
| `CE_SEAT_WATCH_IDLE_THRESHOLD_POLLS` | `5` | Consecutive unchanged polls before `idle_without_signal`; must be at least one. |
| `CE_SEAT_WATCH_DISPATCH_PATTERNS` | `[]` | JSON array of strings to watch for delivery acknowledgements. |
| `CE_SEAT_WATCH_WEBHOOK_FILE` | unset | Absolute path for an optional append-only JSONL mirror. |
| `CE_SEAT_WATCH_ITERATIONS` | unset | Integer poll-pass limit. Useful for one-shot smoke runs. |
| `CE_DAEMON_LEASE_TTL_SECONDS` | `300` | Singleton lease TTL in seconds. |
| `CE_DAEMON_HOLDER_ID` | generated | Optional lease holder id string. |

Example one-shot configuration:

```bash
export CE_SEAT_WATCH_SEAT_PROBES='[{"seat_id":"<seat-id>","argv":["<probe-command>"]}]'
export CE_SEAT_WATCH_FEED_PATH='<feed-path>'
export CE_DAEMON_LEASE_ROOT='<lease-root>'
deploy/seat-watch/launch-seat-watch.sh --one-shot
```

The launcher defaults to host execution for slice 1. It sets `PYTHONPATH` to
the repository validator package and runs:

```bash
python -m creator_engine_validator.seat_watch_runner
```

## Slice 2 Roadmap

- Containerized launch: add a `seat-watch` daemon variant to the shared daemon
  container wrapper.
- Idle-trigger dispatch integration: wire `idle_without_signal` events to the
  intake queue for automatic re-dispatch.
- BLOCKED signal annotation: connect BLOCKED events to ticket annotation through
  a read-only webhook call.
- Webhook/socket fanout: fan events to multiple consumers without modifying the
  core daemon.

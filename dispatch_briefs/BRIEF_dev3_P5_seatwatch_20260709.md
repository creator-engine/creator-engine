# BRIEF — dev-3 — 2026-07-09 — P5: Seat-Watch Daemon Slice 1 (STRANGELOOP-1 pool)

Role: **implementer**. Contained COMMIT-ONLY seat (controller harvests — self-push infra is down).
Fresh worktree `/var/tmp/wt-p5-seatwatch` off `origin/main` (fetch first). Branch
`ce-p5-seatwatch-s1`. Declared work class: **story**.
Signal: `READY ce-p5-seatwatch-s1 <sha> .ce/pr-manifests/ce-p5-seatwatch-s1.md`
or `BLOCKED ce-p5-seatwatch-s1 <reason>`.
NO `.ce/brain/assertions.yaml` edits. SEAT-TARGETED-TESTS-ONLY — full `ce validate-pr` preflight
is controller-side; in-seat tests are targeted unit/smoke tests for new files only.

---

## Authorizing decisions

Decision 16 (STRANGELOOP-1 pool P5); ratified 2026-07-09.
Evidence: two idle-without-signal incidents + dispatch-delivery races on 2026-07-08, plus a 5.5h
controller gap where READY signals sat unseen and required manual catch-up.

---

## Scope: Seat-Watch Daemon — slice 1 (observe-only)

Build a seat-watch daemon at **`deploy/seat-watch/`** and **`validators/creator_engine_validator/`**
that:

1. **Polls configured seat panes** on a configurable interval, reusing the existing
   `SeatProbeSpec` / `subprocess_probe_runner` / `parse_ready_for_harvest_signals` probe
   machinery from `validators/creator_engine_validator/conveyor_discovery.py`. Do NOT
   duplicate probe machinery — import it directly.

2. **Detects and emits structured events** to an append-only JSONL feed
   (`CE_SEAT_WATCH_FEED_PATH`) and an optional webhook-file output
   (`CE_SEAT_WATCH_WEBHOOK_FILE`). Five event types in slice 1:
   - `ready_signal` — READY-FOR-HARVEST sha-bearing signal line detected in pane
   - `blocked_signal` — BLOCKED signal line detected in pane (branch + reason)
   - `idle_without_signal` — pane text hash unchanged for N consecutive polls without any signal
   - `pane_error` — probe failure classified as `limit`, `auth`, `exit_143`, `probe_failed`, or `unknown`
   - `dispatch_delivery_ack` — a watched pointer string became visible in pane text since the previous poll

3. **Observe-only in slice 1** — no dispatch authority, no herdr writes, no `IntakeQueue`
   reads or writes. Pane access is read-only via probe argv.

4. **Ships with**: systemd unit, launcher script (modelled on
   `deploy/conveyor-daemon/launch-conveyor-daemon.sh`), targeted unit tests, and
   a design doc at `deploy/seat-watch/DESIGN.md`.

### Slice 1 deliverables — only these; nothing more

- `deploy/seat-watch/launch-seat-watch.sh` — daemon launcher script
- `deploy/seat-watch/ce-seat-watch.service` — systemd unit
- `deploy/seat-watch/DESIGN.md` — design doc (event schema + config reference + slice 2 roadmap)
- `validators/creator_engine_validator/seat_watch_daemon.py` — daemon core (polling logic,
  event emission, idle tracking, pane error classification, dispatch ack detection, BLOCKED parsing)
- `validators/creator_engine_validator/seat_watch_runner.py` — config/env loading, `main()`
  entrypoint, singleton lease wiring (pattern: `conveyor_daemon_runner.py`)
- `validators/tests/unit/test_seat_watch_daemon.py` — targeted unit tests
- `.ce/pr-manifests/ce-p5-seatwatch-s1.md` — path-manifest carrier
- `.ce/changelog/ce-p5-seatwatch-s1.md` — changelog fragment (work class: story)

NO gating flip. NO assertions.yaml edits. NO modifications to any existing module (import
only). NO modifications to `deploy/daemons/run-daemon-container.sh` (slice 2 adds seat-watch
to the shared container wrapper). NO edits outside the eight paths listed above.

---

## Territory collision check — READ BEFORE TOUCHING ANYTHING

**OFF LIMITS — do not create or modify any file under these paths:**
- `deploy/queue-daemon/*` — branch `ce-512-redeploy-portability` is in flight; any edit = merge conflict
- `deploy/singleton-redeploy/*` — branch `ce-512-redeploy-portability` is in flight; any edit = merge conflict

**IMPORT-ONLY (do not modify, do not copy):**
- `validators/creator_engine_validator/conveyor_discovery.py` — import `SeatProbeSpec`,
  `subprocess_probe_runner`, `parse_ready_for_harvest_signals` from here; do not modify
- `validators/creator_engine_validator/conveyor_daemon_runner.py` — pattern reference only;
  do not modify
- `validators/creator_engine_validator/conveyor_intake_queue.py` — do not import or modify
  in slice 1; seat-watch is independent of the intake queue
- `deploy/daemons/run-daemon-container.sh` — pattern reference only; do not modify

**SAFE HOME — verified absent on origin/main, no collision:**
- `deploy/seat-watch/` — directory does not exist; create new
- `validators/creator_engine_validator/seat_watch_daemon.py` — no existing file
- `validators/creator_engine_validator/seat_watch_runner.py` — no existing file
- `validators/tests/unit/test_seat_watch_daemon.py` — no existing file

If you find any unexpected file at `deploy/seat-watch/` or either `seat_watch_*.py` path
on the fresh worktree, signal:
`BLOCKED ce-p5-seatwatch-s1 territory-collision: unexpected file at <path>`

**Other in-flight branches — no collision expected:**
- `ce-p3-rehearsal-s1` (P3 — rehearsal harness) — homes at `deploy/rehearsal/`; no overlap
- `ce-p2-acceptance-evidence` (P2 — autoclose parser) — homes at `tools/ce-ops-autoclose/`,
  `.github/scripts/ceops_autoclose.py`; no overlap
- `ce-hermes-retirement` (P1 — .hermes retirement) — homes at `ce_onboard.py`, scripts,
  docs; no overlap
- `ce-conveyor-intake-s1` — MERGED to origin/main as commit `402192ddc` on 2026-07-09;
  no in-flight risk; `conveyor_intake_queue.py` is already on main

---

## Grounding: existing probe machinery (origin/main)

All the following machinery is present on origin/main. Base your worktree on origin/main
(fetch first) and import from the package as shown.

### `validators/creator_engine_validator/conveyor_discovery.py` — exports to reuse

```python
from .conveyor_discovery import (
    SeatProbeSpec,                    # frozen dataclass: seat_id: str, argv: tuple[str, ...]
    subprocess_probe_runner,          # ProbeRunner: (argv: Sequence[str]) -> str
    parse_ready_for_harvest_signals,  # (text, *, audit_sink=None, seat_id=None) -> list[ReadyForHarvestSignal]
)
```

`SeatProbeSpec` is a frozen dataclass with two fields: `seat_id: str` and
`argv: Sequence[str]` (normalized to a tuple in `__post_init__`).

`subprocess_probe_runner(argv: Sequence[str]) -> str` runs the argv as a subprocess with
`check=True` and returns stdout. Raises `subprocess.CalledProcessError` on non-zero exit;
exit code 143 means SIGTERM (seat was killed). Wrap all calls in `try/except Exception`.

`parse_ready_for_harvest_signals(pane_text, *, audit_sink=None, seat_id=None)`
returns `list[ReadyForHarvestSignal]`. Each signal has `.branch: str` and `.sha: str`
(`.tag: str | None` may also be present). Returns an empty list if no READY-FOR-HARVEST
line is found. The function strips ANSI escapes and rejects diff-echo lines automatically.

### `validators/creator_engine_validator/conveyor_daemon_runner.py` — pattern to follow

The conveyor daemon runner is the canonical structural pattern. Replicate these elements:

**Config dataclass (frozen):**
```python
@dataclass(frozen=True)
class SeatWatchConfig:
    seat_probes: tuple[SeatProbeSpec, ...]
    feed_path: Path
    lease_root: Path
    interval_seconds: float = 30.0
    idle_threshold_polls: int = 5
    dispatch_patterns: tuple[str, ...] = ()
    webhook_file: Path | None = None
    iterations: int | None = None
    lease_ttl_seconds: float = DEFAULT_LEASE_TTL_SECONDS
    holder_id: str | None = None
```

**Config loader signature:**
```python
def load_config(env: Mapping[str, str] | None = None) -> SeatWatchConfig:
    source = os.environ if env is None else env
    ...
```

Missing required env vars must raise `ConfigError(ValueError)`.

**Lease pattern** (import from existing package module):
```python
from .daemon_lease import (
    DaemonLease,
    DaemonLeaseError,
    DEFAULT_LEASE_TTL_SECONDS,
    acquire,
)
```

**Signal handling** in the poll loop:
```python
stop_event = threading.Event()
signal.signal(signal.SIGTERM, lambda s, _: stop_event.set())
signal.signal(signal.SIGINT, lambda s, _: stop_event.set())
try:
    while not stop_event.is_set():
        daemon.run_once(poll_index)
        poll_index += 1
        if config.iterations is not None and poll_index >= config.iterations:
            break
        stop_event.wait(config.interval_seconds)
finally:
    lease.release()
```

Restore original signal handlers in the finally block (same as `conveyor_daemon_runner.py`).

### `deploy/conveyor-daemon/launch-conveyor-daemon.sh` + `ce-conveyor-daemon.service` — template pattern

**`launch-seat-watch.sh`** must follow the conveyor launcher pattern exactly:
- `usage()` heredoc documenting required and optional env vars
- `die()` helper: `printf 'ERROR: %s\n' "$*" >&2; exit 1`
- `require_env()` local function: dies if `${!name:-}` is empty
- `--health` flag: call `require_env` for all required vars, print `seat-watch daemon: healthy`,
  exit 0
- `--one-shot` flag: run one poll pass only (pass `CE_SEAT_WATCH_ITERATIONS=1`)
- Uncontained launch path (slice 1 default — `CE_DAEMON_UNCONTAINED` defaults to 1):
  ```bash
  exec python -m creator_engine_validator.seat_watch_runner "$@"
  ```
- No secrets baked in; all secrets via env or `CE_DAEMON_ENV_FILE`

**`ce-seat-watch.service`** — follow `ce-conveyor-daemon.service` exactly:
```ini
[Unit]
Description=Creator Engine seat-watch daemon (observe-only, slice 1)
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=300
StartLimitBurst=12

[Service]
Type=simple
User=creator-engine
WorkingDirectory=/workspace/creator-engine
EnvironmentFile=/etc/creator-engine/ce-seat-watch.env
Environment=CE_DAEMON_UNCONTAINED=1
ExecStart=/bin/bash -lc 'exec /workspace/creator-engine/deploy/seat-watch/launch-seat-watch.sh'
Restart=always
RestartSec=5
RuntimeDirectory=ce-seat-watch
RuntimeDirectoryMode=0700
StateDirectory=ce-seat-watch
StateDirectoryMode=0700
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ce-seat-watch

[Install]
WantedBy=multi-user.target
# Slice 1: observe-only. No dispatch authority. Enable only after Operator-gated deployment flip.
```

---

## JSONL event schema

Each write to `CE_SEAT_WATCH_FEED_PATH` (and optionally `CE_SEAT_WATCH_WEBHOOK_FILE`) is
one JSON object per line, appended atomically (write to `.tmp` in same directory, then
`os.replace`). Never truncate the feed file.

Top-level fields present in every event:

```json
{
  "schema_version": "1",
  "event_type": "<type>",
  "seat_id": "<seat_id string>",
  "ts": "<ISO-8601 UTC, e.g. 2026-07-09T06:30:00Z>",
  "poll_index": 42,
  "detail": { ... event-type specific ... }
}
```

### `ready_signal`

```json
{
  "detail": {
    "branch": "<branch-slug>",
    "sha": "<40-hex sha>",
    "tag": "<tag string or null>"
  }
}
```

Emit one event per parsed signal per poll. If `parse_ready_for_harvest_signals` returns
two signals in one poll, emit two separate events.

### `blocked_signal`

```json
{
  "detail": {
    "branch": "<branch-slug>",
    "reason": "<remainder of BLOCKED line after branch>"
  }
}
```

Parsed by `seat_watch_daemon.py` using the pattern:
`re.compile(r"^\s*BLOCKED\s+(\S+)\s+(.+)$", re.MULTILINE)`.
The first capture group is `branch`; everything after the branch on that line is `reason`.
Trim whitespace from both. Emit one event per matched line per poll.
A BLOCKED line resets the idle counter for that seat (same as a READY signal).

### `idle_without_signal`

```json
{
  "detail": {
    "polls_unchanged": 5,
    "pane_hash": "<sha256 hex digest of pane text>"
  }
}
```

Emitted when all of the following hold:
- The SHA-256 hash of the current pane text equals the stored hash from the previous poll
  for this seat (text has not changed)
- The consecutive-unchanged counter for this seat has reached `idle_threshold_polls`
- No `ready_signal` or `blocked_signal` was found in this poll

After emitting, reset the counter to 0 (so the event fires again only after another full
threshold window of unchanged text). If pane text changes at any point, also reset to 0.

### `pane_error`

```json
{
  "detail": {
    "error_class": "limit|auth|exit_143|probe_failed|unknown",
    "detail": "<exception class name and message, first 400 chars>"
  }
}
```

Classification (apply in order; stop at first match):
1. `exit_143` — `subprocess.CalledProcessError` with `returncode == 143`
2. `limit` — exception `str()` contains `"rate limit"`, `"quota"`, or `"429"` (case-insensitive)
3. `auth` — exception `str()` contains `"unauthorized"`, `"401"`, or `"authentication"` (case-insensitive)
4. `probe_failed` — any other `subprocess.CalledProcessError` or `subprocess.TimeoutExpired`
5. `unknown` — any other exception

A `pane_error` does NOT update pane hash state (treat as missing data; do not reset idle counter,
do not advance it either — leave unchanged counter as-is for that seat this poll).

### `dispatch_delivery_ack`

```json
{
  "detail": {
    "pattern_matched": "<the pattern string from CE_SEAT_WATCH_DISPATCH_PATTERNS>",
    "context_line": "<first line of pane text containing the match, truncated at 200 chars>"
  }
}
```

Emitted when a string from `CE_SEAT_WATCH_DISPATCH_PATTERNS` (case-insensitive substring
match) is present in the current poll's pane text AND was absent in the previous poll's
pane text for that seat. This detects the moment a dispatched pointer message became visible.

Emit one event per newly-appearing pattern. If a pattern appears in polls 2, 3, 4 (unchanged),
emit only once (on poll 2 when it first appears). The "previous pane text" is the last
successful probe result; errors do not update the previous text.

---

## Config environment variables

### Required

| Variable | Description |
|---|---|
| `CE_SEAT_WATCH_SEAT_PROBES` | JSON array: `[{"seat_id":"dev-3","argv":["herdr","pane","read","w1:p1","--source","recent","--lines","80"]}]` Same format as `CE_CONVEYOR_DAEMON_SEAT_PROBES`. |
| `CE_SEAT_WATCH_FEED_PATH` | Absolute path to the append-only JSONL event feed. Created if absent. |
| `CE_DAEMON_LEASE_ROOT` | Singleton lease root directory (shared convention across all CE daemons). |

### Optional

| Variable | Default | Description |
|---|---|---|
| `CE_SEAT_WATCH_INTERVAL_SECONDS` | `30` | Poll interval in seconds; must be > 0. |
| `CE_SEAT_WATCH_IDLE_THRESHOLD_POLLS` | `5` | Consecutive unchanged polls before emitting `idle_without_signal`; must be >= 1. |
| `CE_SEAT_WATCH_DISPATCH_PATTERNS` | `[]` | JSON array of strings; each is a case-insensitive substring to watch for delivery acks. |
| `CE_SEAT_WATCH_WEBHOOK_FILE` | unset | Absolute path; if set, each event is appended here (same format as feed). |
| `CE_SEAT_WATCH_ITERATIONS` | unset | Integer; if set, stop after this many poll passes and exit 0. |
| `CE_DAEMON_LEASE_TTL_SECONDS` | `DEFAULT_LEASE_TTL_SECONDS` | Lease TTL in seconds. |
| `CE_DAEMON_HOLDER_ID` | `seat-watch:<hostname>:<pid>` | Optional lease holder id string. |

---

## Implementation notes for `seat_watch_daemon.py`

Keep the daemon class and runner separate so tests can inject fakes.

### `SeatWatchDaemon` class

```python
class SeatWatchDaemon:
    def __init__(
        self,
        specs: Sequence[SeatProbeSpec],
        *,
        idle_threshold_polls: int = 5,
        dispatch_patterns: Sequence[str] = (),
        probe_runner: ProbeRunner | None = None,
        now: Callable[[], str] | None = None,
    ) -> None:
        ...

    def run_once(self, poll_index: int) -> list[WatchEvent]:
        """Run one poll pass. Returns all events from this pass."""
        ...
```

Internal per-seat state (maintained between `run_once` calls):
- `_pane_hashes: dict[str, str]` — seat_id → SHA-256 hex of last successful pane text
- `_pane_texts: dict[str, str]` — seat_id → last successful pane text (for dispatch ack diffing)
- `_unchanged_counts: dict[str, int]` — seat_id → consecutive unchanged poll count

For each spec in `self.specs`:
1. Call `probe_runner(spec.argv)` (default: `subprocess_probe_runner`). On exception: classify,
   yield `pane_error` event, skip remaining steps for this seat.
2. Compute `current_hash = hashlib.sha256(pane_text.encode()).hexdigest()`.
3. Check `parse_ready_for_harvest_signals(pane_text)` → yield a `ready_signal` event for each result.
4. Check BLOCKED pattern → yield a `blocked_signal` event for each match.
5. Any signal found (ready or blocked): reset `_unchanged_counts[seat_id] = 0`.
6. If no signal found:
   - If `current_hash == _pane_hashes.get(seat_id)`: increment `_unchanged_counts[seat_id]`.
   - Else: reset `_unchanged_counts[seat_id] = 0`.
   - If count >= `idle_threshold_polls`: yield `idle_without_signal`; reset count to 0.
7. Check dispatch patterns against `pane_text` vs `_pane_texts.get(seat_id, "")`:
   for each pattern in `dispatch_patterns`:
     if pattern (lower) in pane_text.lower() and pattern (lower) not in previous_text.lower():
       yield `dispatch_delivery_ack`.
8. Update `_pane_hashes[seat_id] = current_hash`.
9. Update `_pane_texts[seat_id] = pane_text`.

### `WatchEvent` dataclass

```python
@dataclass(frozen=True)
class WatchEvent:
    schema_version: str
    event_type: str
    seat_id: str
    ts: str
    poll_index: int
    detail: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return dataclasses.asdict(self)
```

### `seat_watch_runner.py` — entrypoint

The runner `main()` must:
1. Call `load_config()` — any `ConfigError` → print to stderr, exit 2.
2. Create `config.feed_path.parent` if absent (mode 0700).
3. Acquire lease via `acquire("seat-watch", holder_id, state_root=config.lease_root, ttl_seconds=...)`.
   Any `DaemonLeaseError` → print to stderr, exit 73.
4. Construct `SeatWatchDaemon(config.seat_probes, idle_threshold_polls=config.idle_threshold_polls,
   dispatch_patterns=config.dispatch_patterns)`.
5. Enter poll loop with SIGTERM/SIGINT handling.
6. On each pass: call `daemon.run_once(poll_index)`, write each event to feed file and
   optionally to webhook file.
7. Release lease in `finally`.

Event writing helper — atomic append:
```python
def _write_event(path: Path, event: WatchEvent) -> None:
    line = json.dumps(event.as_dict(), sort_keys=True, default=str) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=".seat-watch-event.", dir=str(path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
```

(Simpler is fine too — just don't truncate the feed file.)

**`__main__` entry**: add `if __name__ == "__main__": raise SystemExit(main())` so
`python -m creator_engine_validator.seat_watch_runner` works.

---

## Targeted in-seat tests

**`validators/tests/unit/test_seat_watch_daemon.py`** must pass with `pytest` from the
worktree root. No network, no Docker, no real pane access. Use inline fakes.

### Required test cases

1. **`test_ready_signal_emitted`** — stub probe returns a line containing
   `READY-FOR-HARVEST ce-p5-seatwatch-s1 abc1234567890abcdef1234567890abcdef123456`.
   Assert one `ready_signal` event emitted; `detail.branch == "ce-p5-seatwatch-s1"`;
   `detail.sha == "abc1234567890abcdef1234567890abcdef123456"`.

2. **`test_blocked_signal_emitted`** — stub probe returns a line:
   `BLOCKED ce-p5-seatwatch-s1 territory-collision: unexpected file`.
   Assert one `blocked_signal` event; `detail.branch == "ce-p5-seatwatch-s1"`;
   `detail.reason == "territory-collision: unexpected file"`.

3. **`test_idle_without_signal_emitted`** — stub probe always returns same text with no signal.
   Call `run_once` 5 times (`idle_threshold_polls=5`). Assert `idle_without_signal` emitted
   exactly once (on poll index 4, the 5th call). Assert `detail.polls_unchanged == 5`.

4. **`test_idle_resets_on_text_change`** — stub probe returns same text for polls 0–3 then
   different text on poll 4. Threshold is 5. Assert no `idle_without_signal` event across
   all 5 calls.

5. **`test_idle_resets_after_emission`** — threshold is 3. Stub returns same text throughout.
   Calls: 0, 1, 2 → emit on call 2. Calls: 3, 4, 5 → emit again on call 5. Assert two
   `idle_without_signal` events total.

6. **`test_pane_error_exit_143`** — stub raises
   `subprocess.CalledProcessError(143, ["herdr", "pane", "read", "w1:p1"])`.
   Assert `pane_error` event with `detail.error_class == "exit_143"`.

7. **`test_pane_error_auth`** — stub raises `RuntimeError("unauthorized: token invalid")`.
   Assert `pane_error` with `error_class == "auth"`.

8. **`test_pane_error_limit`** — stub raises `RuntimeError("rate limit exceeded (429)")`.
   Assert `pane_error` with `error_class == "limit"`.

9. **`test_pane_error_probe_failed`** — stub raises
   `subprocess.CalledProcessError(1, ["herdr", "pane", "read", "w1:p1"])`.
   Assert `pane_error` with `error_class == "probe_failed"`.

10. **`test_pane_error_unknown`** — stub raises `ValueError("something unexpected")`.
    Assert `pane_error` with `error_class == "unknown"`.

11. **`test_dispatch_delivery_ack_emitted`** — dispatch pattern: `"DISPATCH POINTER"`.
    Poll 0: pane text lacks pattern. Poll 1: pane text contains `"DISPATCH POINTER abc.md"`.
    Assert `dispatch_delivery_ack` emitted on poll 1; `detail.pattern_matched == "DISPATCH POINTER"`.

12. **`test_dispatch_no_duplicate_ack`** — same pattern present in polls 1, 2, 3.
    Assert `dispatch_delivery_ack` emitted only once (poll 1).

13. **`test_dispatch_ack_case_insensitive`** — pattern `"dispatch pointer"`;
    pane text contains `"DISPATCH POINTER"`. Assert ack emitted.

14. **`test_config_load_happy_path`** — supply all required env vars with valid values;
    assert `SeatWatchConfig` fields parse correctly, including `seat_probes` length,
    `interval_seconds`, `idle_threshold_polls`, `dispatch_patterns` tuple.

15. **`test_config_missing_required`** — omit `CE_SEAT_WATCH_SEAT_PROBES`; assert `ConfigError`.

16. **`test_config_bad_json_probes`** — `CE_SEAT_WATCH_SEAT_PROBES="not-json"`;
    assert `ConfigError`.

17. **`test_config_missing_feed_path`** — omit `CE_SEAT_WATCH_FEED_PATH`; assert `ConfigError`.

18. **`test_config_invalid_interval`** — `CE_SEAT_WATCH_INTERVAL_SECONDS="0"`;
    assert `ConfigError`.

19. **`test_config_invalid_idle_threshold`** — `CE_SEAT_WATCH_IDLE_THRESHOLD_POLLS="0"`;
    assert `ConfigError`.

20. **`test_multiple_seats`** — two `SeatProbeSpec` entries; probe for seat-A returns READY,
    probe for seat-B returns unchanged text. Assert `ready_signal` from seat-A and no
    cross-contamination of idle state between seats.

Run with: `python -m pytest validators/tests/unit/test_seat_watch_daemon.py -v`
from the worktree root. All 20 must pass.

---

## `deploy/seat-watch/DESIGN.md` content guidance

Three to four sections, 150–250 lines total. Public artifact — no internal host names,
seat identities, or token names.

**§1 Purpose** — observe-only daemon that closes the controller awareness gap: polls seat
panes on a configurable interval, emits structured JSONL events, feeds controller visibility
without requiring manual pane reads. Slice 1 = read-only; no dispatch authority.

**§2 Event schema** — reproduce the five event type definitions from this brief as a
Markdown table or fenced-JSON blocks.

**§3 Configuration** — reproduce the required/optional env var table from this brief.
Use `<your-feed-path>`, `<lease-root>`, `<probe-command>` as placeholders.

**§4 Slice 2 roadmap** (brief bulleted list):
- (a) Containerized launch: add `seat-watch` daemon variant to `deploy/daemons/run-daemon-container.sh`
- (b) Idle-trigger dispatch integration: wire `idle_without_signal` events to `IntakeQueue` for automatic re-dispatch
- (c) BLOCKED signal → ce-ops ticket annotation (read-only webhook call)
- (d) Webhook/socket fanout: fan events to multiple consumers without modifying the core daemon

---

## Carrier + changelog

**`.ce/pr-manifests/ce-p5-seatwatch-s1.md`** — path-manifest carrier listing all 8 paths
this PR adds. Compute `AUTHORIZED_PATHS_COUNT: 8` and `AUTHORIZED_PATHS_SHA256` over the
sorted list of relative paths. Include the carrier file itself in the count and hash. Follow
the same format as existing carriers under `.ce/pr-manifests/`.

**`.ce/changelog/ce-p5-seatwatch-s1.md`** — one-paragraph changelog fragment, work class story:

> Add seat-watch daemon slice 1 (observe-only) at `deploy/seat-watch/`: polls configured seat
> panes on a configurable interval, emits structured JSONL events (`ready_signal`,
> `blocked_signal`, `idle_without_signal`, `pane_error`, `dispatch_delivery_ack`), ships with a
> systemd unit, launcher script, 20 targeted unit tests, and a design doc. Reuses existing
> seat-probe argv machinery from `conveyor_discovery`; singleton lease; no dispatch authority
> in slice 1.

---

## Public lens

`deploy/seat-watch/DESIGN.md` and `deploy/seat-watch/launch-seat-watch.sh` are published
alongside the rest of `deploy/`. Do not embed internal seat names (`ce-dev-3`, `ce-dgx-codex`,
`spark-b824`), internal hostnames, or token variable names in any shipped file. Use
`<seat-id>`, `<probe-command>`, `<feed-path>`, `<lease-root>` as placeholders in
documentation and comments.

# BRIEF — dev-4 — 2026-07-08 — BATCH: conveyor intake-queue wiring + materializer pre-arming

Role: **implementer**. Contained COMMIT-ONLY seat (ce-dgx-codex). No venv activation needed;
use the installed `ce`.

---

## BORN-A-FOREMAN EXECUTION MODEL

You drive multiple tickets concurrently: **one git worktree + background subagent-thread per
ticket**. Serialize any two tickets that need the same file (see disjointness analysis below —
these two units are disjoint, so both threads may run simultaneously). Report **PER-TICKET**: one
READY or BLOCKED signal per unit before your session ends. Never merge unit work across branches
or worktrees. A unit that is BLOCKED does not block the other unit from signaling READY.

Signal format per unit:

```
READY <branch> <40-char-sha> <carrier-path>
BLOCKED <branch> <one-line reason>
```

---

## PREFLIGHT PRECONDITION — fetch first

Before starting either thread, run:

```bash
git fetch origin
git log origin/main --oneline | head -5
```

Confirm the head commit is `4fae126d179f1c9cf7d618c268ca334036cdc8d7` (fix review followups
batch two, #905) or a later commit. If a new commit has landed since this brief was composed,
proceed — use the actual current `origin/main` HEAD as the base for both branches.

**Do not touch `.ce/brain/assertions.yaml` in either unit.** The brain-ledger tail is reserved
for the dev-1 hermes-retirement unit (BRIEF_dev1_hermes_retirement_R2_20260708.md) which depends
on the assertion count established by PR #907 (ce-readme-overhaul). If any gate in either unit
demands a ledger append, write BLOCKED immediately and stop that thread.

---

## DISJOINTNESS ANALYSIS (read before starting any thread)

**Unit A files** (conveyor intake queue):
- `validators/creator_engine_validator/conveyor_intake_queue.py` (new)
- `validators/creator_engine_validator/conveyor_daemon_runner.py` (modify: new env var + config field + optional intake wiring)
- `validators/tests/unit/test_conveyor_intake_queue.py` (new)
- `docs/design/conveyor-intake-queue.md` (new, docs stub)
- `.ce/changelog/ce-conveyor-intake-s1.md` (new)
- `.ce/pr-manifests/ce-conveyor-intake-s1.md` (new)

**Unit B files** (materializer pre-arming):
- `validators/creator_engine_validator/brain_intent_materializer.py` (modify: ACTOR_VERSION, path.resolve, HeldError comment)
- `validators/creator_engine_validator/pr_preflight.py` (modify: XOR integration test wiring or extend existing test)
- `validators/tests/unit/test_pr_preflight.py` (extend: add XOR-via-run_preflight integration test)
- `validators/tests/unit/test_brain_intent_materializer_hold.py` (extend: path.resolve dot-dot test)
- `.ce/changelog/ce-491-prearming.md` (new)
- `.ce/pr-manifests/ce-491-prearming.md` (new)

**Dev-1 in-flight hermes paths** (BRIEF_dev1_hermes_retirement_R2_20260708.md):
`ce_onboard.py`, `ce_cli.py`, `.claude/hooks/ce-*.sh`, `docs/delivery/*`,
`docs/architecture/*`, `CONTRIBUTING.md`, `docs/contracts/*`, `docs/decisions/*`,
`.gitignore`, `validators/tests/unit/test_dgx_runsc.py`,
`validators/tests/unit/test_vps_runsc_launcher.py`, `.ce/brain/assertions.yaml`

**Open PR #907** (ce-readme-overhaul, branch `ce-readme-overhaul`):
`README.md`, `.ce/brain/assertions.yaml`, `docs/reference/cli.md`,
`validators/creator_engine_validator/checks/version_drift.py`,
`validators/tests/unit/test_ce_brain_drift.py`,
`validators/tests/unit/test_v1_docs_reconciliation.py`,
`validators/tests/unit/test_version_drift.py`

**Collision verdict:**
- Unit A vs Unit B: **CLEAR** — no shared files.
- Unit A vs dev-1 hermes: **CLEAR** — no shared files.
- Unit B vs dev-1 hermes: **CLEAR** — no shared files.
- Unit A vs PR #907: **CLEAR** — no shared files.
- Unit B vs PR #907: **CLEAR** — no shared files.
- `assertions.yaml` is claimed by BOTH dev-1 hermes AND PR #907; forbidden to both units
  (see preflight precondition above). Not a collision between our units.

---

## UNIT A — conveyor intake-queue wiring

**Branch:** `ce-conveyor-intake-s1`
**Worktree:** `/var/tmp/wt-conveyor-intake`
**Work class:** story (S)
**Carrier slug must match branch exactly:** `ce-conveyor-intake-s1`

### Problem statement (grounded in code on origin/main)

CE-410's conveyor daemon is armed and merged. All of the following exist on `origin/main`:

- `validators/creator_engine_validator/conveyor_daemon_runner.py` — shadow-mode launcher;
  `ConveyorDaemonConfig` has `seat_probes`, `runtime_root`, `discovery_state`; config is
  loaded from env (`CE_CONVEYOR_DAEMON_SEAT_PROBES`, `CE_CONVEYOR_DAEMON_RUNTIME_ROOT`,
  `CE_CONVEYOR_DAEMON_DISCOVERY_STATE`, `CE_DAEMON_LEASE_ROOT`, etc.); `_build_daemon`
  constructs the daemon with a `ConveyorSeatDiscoveryRunner`.
- `validators/creator_engine_validator/conveyor_discovery.py` — `ConveyorSeatDiscoveryRunner`
  polls seat pane text for `READY-FOR-HARVEST` signals; the `discovery_state` path tracks
  which `(seat_id, branch, sha)` tuples have already been processed.
- `validators/creator_engine_validator/conveyor_daemon.py` — `ConveyorDaemon.run_once()`
  calls `self.discovery_runner()` to get discovered items, then either plans (disarmed) or
  processes them (armed). Disarmed mode logs `"conveyor dry-run plan <branch>: ..."`.
- `deploy/conveyor-daemon/launch-conveyor-daemon.sh` — host/container launcher.
- `deploy/daemons/run-daemon-container.sh` — routes `conveyor-daemon` to the launch script;
  mounts state under `$CE_DAEMON_STATE_ROOT/conveyor-daemon/` with sub-paths:
  `runtime`, `discovery-state.json`, `conveyor-daemon-ledger.jsonl`,
  `side-effect-ledger`, `active-work-ledger`.

**What is missing:** the INTAKE side. The discovery runner is REACTIVE — seats signal
readiness AFTER work is done (output side). There is no mechanism by which:
1. The controller can stock a queue of ready-to-dispatch ticket-units.
2. The daemon detects an idle seat (one whose pane returned no READY signal) and surfaces
   the next pending unit as a planned dispatch.

Result: 3/3 seats sat idle today against a 157-ticket backlog because the controller still
hand-authors briefs and manually sends them to seats. The factory cannot self-feed.

### Deliverable — ONE story slice

Implement the file-based intake queue and dry-run wiring. No live dispatch authority in
this slice. Everything is flag-gated (`CE_CONVEYOR_INTAKE_ENABLED`, default absent = off).

**Before writing any code**, probe `origin/main` to confirm the intake queue is not already
partially implemented:

```bash
git show origin/main:validators/creator_engine_validator/conveyor_intake_queue.py 2>&1 | head -5
# Expect: "fatal: Path … does not exist" — confirms no prior implementation.

git show origin/main:validators/creator_engine_validator/conveyor_daemon_runner.py | \
  grep -n 'intake\|INTAKE'
# Expect: zero hits — confirms no env var wiring exists.
```

If either probe returns real content, note in the READY signal what was already present and
scope the work to what actually remains.

**S-1: New module `validators/creator_engine_validator/conveyor_intake_queue.py`**

Implements file-based FIFO intake queue matching the existing `discovery-state/runtime` layout
under `.ce/state/conveyor-daemon/intake-queue/` (or a configurable root). Requirements:

- `IntakeQueue(root: Path)` class with:
  - `stock(unit: IntakeUnit) -> None` — write a unit file atomically to `pending/`; unit
    filename is `{priority:05d}-{unit_id}.yaml` (zero-padded priority for FIFO ordering).
  - `claim_next() -> IntakeUnit | None` — atomically rename the lexicographically first file
    from `pending/` to `claimed/`; return None if queue is empty. Use `os.replace` for
    atomicity.
  - `list_pending() -> list[IntakeUnit]` — return pending units in claim order (sorted by
    filename).
  - `mark_done(unit_id: str) -> None` — move a claimed unit to `done/`.

- `IntakeUnit` dataclass with fields: `unit_id: str`, `brief_ref: str` (path or pointer to
  the brief), `branch: str`, `worktree: str`, `priority: int`, `work_class: str`,
  `status: str` (literal `"pending" | "claimed" | "done"`), `created_at: str` (ISO-8601 Z).
  Serializes to/from YAML (use stdlib `json` as an alternative if PyYAML is not available in
  the seat image — check with `python3 -c "import yaml"` and fall back to JSON if absent).

- `IntakeQueueReader(queue: IntakeQueue, seat_probe_results: Mapping[str, bool])` — given a
  mapping of `seat_id → had_ready_signal`, yields `IntakeDispatchPlan` items for each idle
  seat (had_ready_signal=False) paired with the next pending unit. In this slice the plan is
  READ-ONLY: no unit is claimed, no message is sent to the seat. This is pure planning output.

- `IntakeDispatchPlan` dataclass: `seat_id: str`, `unit: IntakeUnit`, `action: str`
  (always `"WOULD_DISPATCH"` in this slice).

**S-2: Wire into `conveyor_daemon_runner.py`**

Add to `ConveyorDaemonConfig`:
```python
intake_queue_root: Path | None = None
intake_enabled: bool = False
```

Add to `load_config()`:
```python
intake_queue_root=_optional_path(source, "CE_CONVEYOR_INTAKE_QUEUE_ROOT"),
intake_enabled=source.get("CE_CONVEYOR_INTAKE_ENABLED", "").strip() == "1",
```

In `_build_daemon` (or in `_run_loop`), after `daemon.run_once()`, if `config.intake_enabled`
and `config.intake_queue_root` is set, instantiate `IntakeQueue(config.intake_queue_root)` and
`IntakeQueueReader`. Log the plans via `_log(...)` — one line per plan:
`"conveyor-intake dry-run: WOULD_DISPATCH unit <unit_id> (branch <branch>) to seat <seat_id>"`.

Do NOT call `claim_next()` in this slice — the log is the only side effect.

The seat probe results needed by `IntakeQueueReader` come from the daemon's discovery pass:
if a seat probe returned zero READY signals in the current pass, it is idle. Capture this
from `ConveyorDaemonRunResult` and pass it to the reader.

**S-3: Tests** (`validators/tests/unit/test_conveyor_intake_queue.py`)

Required test cases (at minimum):
1. `test_stock_creates_pending_file` — stock one unit; verify `pending/` contains exactly one
   `.yaml` (or `.json`) file named with the correct priority prefix.
2. `test_claim_next_returns_oldest_pending` — stock two units with different priorities; verify
   `claim_next()` returns the lower-priority (higher-urgency) one and moves it to `claimed/`.
3. `test_claim_next_returns_none_when_empty` — empty queue; verify `claim_next()` returns None.
4. `test_mark_done_moves_to_done` — stock then claim then mark_done; verify file is in `done/`.
5. `test_list_pending_returns_sorted_order` — stock three units; verify list order.
6. `test_intake_queue_reader_plans_idle_seats` — given one idle seat and one pending unit,
   verify reader yields one `IntakeDispatchPlan` with `action="WOULD_DISPATCH"`.
7. `test_intake_queue_reader_skips_busy_seats` — given one seat with `had_ready_signal=True`,
   verify reader yields nothing.
8. `test_load_config_intake_disabled_by_default` — call `load_config` with minimal valid env
   (no `CE_CONVEYOR_INTAKE_ENABLED`); verify `config.intake_enabled is False`.
9. `test_load_config_intake_enabled_when_flag_set` — set `CE_CONVEYOR_INTAKE_ENABLED=1`;
   verify `config.intake_enabled is True`.

**S-4: Docs stub** (`docs/design/conveyor-intake-queue.md`)

A short design note (8–16 lines) covering: what the intake queue is, the file layout under
`.ce/state/conveyor-daemon/intake-queue/`, the three state directories (`pending/claimed/done`),
the flag gate, and a note that live dispatch is slice-2 scope.

### Hard constraints

- Flag-gated: without `CE_CONVEYOR_INTAKE_ENABLED=1` the daemon's behaviour is identical to
  `origin/main`. Zero behavioral change when the flag is absent.
- No live dispatch, no subprocess calls to seats, no writes to any pane or herdr socket.
- No new required env vars (all new vars are optional).
- Do not weaken or restructure the existing `ConveyorSeatDiscoveryRunner` or
  `ConveyorDaemon.run_once()` logic; only ADD paths that activate under the flag.
- PRODUCT LENS: zero ce-ops# references in the docs stub.
- Do NOT touch `README.md`, `.ce/brain/assertions.yaml`, `checks/version_drift.py`, or any
  other file outside the STOP LINE.

### Standing preflight directive (ce-ops#303)

Full `ce validate-pr --profile contained-seat` green before signaling READY. Known seat-env
false-REDs (proven 2026-07-08, controller has evidence): control-plane portability gate and
check-examples/libsodium may fail in this seat's image on paths OUTSIDE your diff — if the
ONLY failures are those two gates on files you did not touch, note them verbatim and signal
READY anyway. Any failure touching YOUR changed files = fix or BLOCKED.

### STOP LINE (Unit A)

No pushes, no PRs, no gate acts. Only these paths:

```
validators/creator_engine_validator/conveyor_intake_queue.py
validators/creator_engine_validator/conveyor_daemon_runner.py
validators/tests/unit/test_conveyor_intake_queue.py
docs/design/conveyor-intake-queue.md
.ce/changelog/ce-conveyor-intake-s1.md
.ce/pr-manifests/ce-conveyor-intake-s1.md
.ce/wt-conveyor-intake/READY
.ce/wt-conveyor-intake/BLOCKED
```

Carrier: slug `ce-conveyor-intake-s1` exactly; every changed path enumerated; exactly ONE
`- **Declared work class:** S` line.

### READY / BLOCKED signals (Unit A)

**When DONE — write `.ce/wt-conveyor-intake/READY` then emit to pane:**
```
STATUS: READY
BRANCH: ce-conveyor-intake-s1
COMMIT: <HEAD SHA after final commit>
CARRIER: .ce/pr-manifests/ce-conveyor-intake-s1.md
PROBE_INTAKE_MODULE: <"not_found" | "found: <path>:<line>" if already partially present>
FLAG_GATED: yes
INTAKE_ENABLED_DEFAULT: off
VALIDATE_PR: GREEN
GATE_NOISE: <"none" or verbatim text of external false-RED gates on untouched files>
READY ce-conveyor-intake-s1 <sha> .ce/pr-manifests/ce-conveyor-intake-s1.md
```
Commit the signal file as the FINAL commit on the branch before stopping.

**When BLOCKED — write `.ce/wt-conveyor-intake/BLOCKED` then emit:**
```
STATUS: BLOCKED
BRANCH: ce-conveyor-intake-s1
BLOCKER: <one-sentence description>
CONTEXT: <full context, file/line/error>
BLOCKED ce-conveyor-intake-s1 <reason>
```

---

## UNIT B — materializer pre-arming checklist batch

**Branch:** `ce-491-prearming`
**Worktree:** `/var/tmp/wt-491-prearming`
**Work class:** task (T)
**Carrier slug must match branch exactly:** `ce-491-prearming`

### Problem statement

PRs #902 and #904 (CE-491 Option A materializer slices 1 and 2) are merged. The controller's
review at merge time tracked four findings that must be closed before the materializer can be
armed. All four are confirmed OPEN on `origin/main` at `4fae126d1` (verified by the controller
before composing this brief). Address all four. See probe commands below to confirm each item
is still open before editing.

### Finding 1 — XOR run_preflight integration test

**Source:** PR #904 review (ce-dev-2, 2026-07-08T12:36:13Z):
> "MINOR: no integration test exercising the XOR gate via `run_preflight`'s real sequence — a
> reorder/skip regression would be uncaught. Add before arming."

**Context:** `brain_append_intent_xor_direct_ledger` is registered in `run_preflight` at
`validators/creator_engine_validator/pr_preflight.py:1135-1136`:
```python
"Creator Engine validator - brain_append_intent_xor_direct_ledger",
lambda: _assert_brain_append_intent_xor(config, comparison_base["value"], runner),
```
The gate was wired in #904 but no test exercises `run_preflight`'s actual call sequence to
verify the gate is invoked and cannot be silently skipped by a reorder.

**Probe before editing:**
```bash
git show origin/main:validators/tests/unit/test_pr_preflight.py | \
  grep -n 'xor\|brain_append_intent\|XOR'
# Expect: zero hits — confirms no XOR-via-run_preflight test exists.
```
If the probe returns hits, drop this item and note `PROBE_ITEM1: already_resolved` in the
READY signal.

**Deliverable:** Add a test in `validators/tests/unit/test_pr_preflight.py` that calls
`run_preflight` (or its inner check-runner) with a changed-paths set containing both a
`brain_append_intent_*.yaml` file AND a `.ce/brain/assertions.yaml` path, and asserts the
XOR gate fires (returns a non-OK result). Also assert the gate does NOT fire when only the
intent file is changed (no ledger file in diff) — this validates the XOR logic direction.
Use fakes/stubs for git runner as the existing tests in that file do.

### Finding 2 — ACTOR_VERSION bump

**Source:** PR #904 review (ce-dev-2, 2026-07-08T12:36:13Z):
> "MINOR: `ACTOR_VERSION` still \"ce-491-optiona-slice1\" — audit records from slice-2 code
> are ambiguous. Bump next touch."

**Context:** `validators/creator_engine_validator/brain_intent_materializer.py:32`:
```python
ACTOR_VERSION = "ce-491-optiona-slice1"
```
Slice-2 code (HistoryScanner, CloseoutWindowPolicy, MaterializerRunLoop) emits audit records
stamped with this version string, making it ambiguous which slice generated a given record.

**Probe before editing:**
```bash
git show origin/main:validators/creator_engine_validator/brain_intent_materializer.py | \
  grep -n 'ACTOR_VERSION'
# Expect: line 32: ACTOR_VERSION = "ce-491-optiona-slice1"
```
If the probe shows a version string other than `"ce-491-optiona-slice1"`, note
`PROBE_ITEM2: already_resolved` and drop this item.

**Deliverable:** Change line 32 of `brain_intent_materializer.py`:
```python
# BEFORE:
ACTOR_VERSION = "ce-491-optiona-slice1"
# AFTER:
ACTOR_VERSION = "ce-491-prearming"
```
No other changes needed for this item.

### Finding 3 — path.resolve() in _require_state_subtree

**Source:** PR #904 review (ce-dev-2, 2026-07-08T12:36:13Z):
> "NIT: `_require_state_subtree` lacks `path.resolve()` normalization (theoretical `..`
> traversal; unexploitable today, callers are trusted) — normalize before arming."

**Context:** `validators/creator_engine_validator/brain_intent_materializer.py:236-244`
(current code on origin/main):
```python
def _require_state_subtree(path: Path) -> None:
    parts = path.parts
    for index, part in enumerate(parts[:-1]):
        # The prior index-bound check was always true here: iterating parts[:-1]
        # guarantees one following part whenever ".ce" is visited.
        if part == ".ce" and parts[index + 1] == "state":
            return
    raise RuntimeError(f"materializer evidence path escapes .ce/state: {path}")
```
A path like `Path("/workspace/creator-engine/.ce/state/../../../etc/shadow")` passes the
string check but resolves outside `.ce/state`. Normalizing with `path.resolve()` before
inspecting `parts` closes this gap.

**Probe before editing:**
```bash
git show origin/main:validators/creator_engine_validator/brain_intent_materializer.py | \
  sed -n '234,248p'
# Expect: _require_state_subtree with no path.resolve() call.
```
If the probe shows `path.resolve()` already present, note `PROBE_ITEM3: already_resolved`.

**Deliverable — two changes:**

1. In `brain_intent_materializer.py`, add `path = path.resolve()` as the first statement of
   `_require_state_subtree`:
   ```python
   def _require_state_subtree(path: Path) -> None:
       path = path.resolve()
       parts = path.parts
       for index, part in enumerate(parts[:-1]):
           ...
   ```

2. In `validators/tests/unit/test_brain_intent_materializer_hold.py`, add a test proving the
   dot-dot traversal is rejected:
   ```python
   def test_require_state_subtree_rejects_dotdot_traversal(tmp_path):
       # A path that contains .ce/state in its string form but resolves outside it
       # must be rejected after normalization.
       # Build: <tmp_path>/.ce/state/../../../outside/key.json
       base = tmp_path / ".ce" / "state"
       base.mkdir(parents=True)
       traversal = base / ".." / ".." / ".." / "outside" / "key.json"
       with pytest.raises(RuntimeError, match="escapes .ce/state"):
           _require_state_subtree(traversal)
   ```
   Note: `path.resolve()` requires the path's ancestor directories to exist in order to
   resolve correctly on some platforms. Create the `.ce/state` directory in `tmp_path` before
   constructing the traversal path, so resolve() has a real anchor.

### Finding 4 — HeldError asymmetry comment

**Source:** PR #904 review (ce-dev-2, 2026-07-08T12:36:13Z):
> "NIT: HeldError handler lacks the parallel asymmetry comment."

**Context:** `validators/creator_engine_validator/brain_intent_materializer.py`.
The `BrainAppendRefusal` except handler (line 774-776 on origin/main) has the comment:
```python
except BrainAppendRefusal as exc:
    # Artifact asymmetry: BrainAppendRefusal writes quarantine,
    # HELD state, dry-run artifact, and JSONL event; HeldError
    # writes HELD state and JSONL event only.
```
The `HeldError` except handler (line 820 on origin/main) has no parallel comment, making the
artifact surface of each exception path harder to audit.

**Probe before editing:**
```bash
git show origin/main:validators/creator_engine_validator/brain_intent_materializer.py | \
  grep -n -A2 'except HeldError'
# Expect: no asymmetry comment immediately after "except HeldError as exc:"
```
If the probe shows an asymmetry comment already present, note `PROBE_ITEM4: already_resolved`.

**Deliverable:** Add the parallel comment immediately after `except HeldError as exc:` at
line 820:
```python
except HeldError as exc:
    # Artifact asymmetry: HeldError writes HELD state and JSONL event only
    # (no quarantine, no dry-run artifact — contrast BrainAppendRefusal handler above).
    key = fallback_key
    ...
```

### Acceptance criteria (Unit B)

All of the following must hold before signaling READY:

1. `grep ACTOR_VERSION validators/creator_engine_validator/brain_intent_materializer.py`
   returns `ce-491-prearming` (or a note that it was already bumped).
2. `grep -n 'path.resolve' validators/creator_engine_validator/brain_intent_materializer.py`
   returns a hit inside `_require_state_subtree` (or PROBE_ITEM3 already_resolved).
3. `grep -n 'asymmetry' validators/creator_engine_validator/brain_intent_materializer.py`
   returns TWO hits — one in the BrainAppendRefusal handler and one in the HeldError handler
   (or PROBE_ITEM4 already_resolved).
4. `pytest validators/tests/unit/test_brain_intent_materializer_hold.py -v` passes.
5. `pytest validators/tests/unit/test_pr_preflight.py -v` passes (or PROBE_ITEM1
   already_resolved).
6. Full `ce validate-pr --profile contained-seat` green on the diff (known seat false-REDs
   exempt as above).

### Hard constraints

- Do NOT touch `.ce/brain/assertions.yaml` — see preflight precondition.
- Do NOT touch `README.md`, `checks/version_drift.py`, or any file outside the STOP LINE.
- Do NOT touch `conveyor_daemon_runner.py` or any Unit A file — parallel thread owns those.
- `ARMING_ENABLED` in `brain_intent_materializer.py` must remain `False` — this unit is
  pre-arming checklist cleanup ONLY, not the arming act itself.

### Standing preflight directive (ce-ops#303)

Full `ce validate-pr --profile contained-seat` green before signaling READY. Same known
false-RED exemptions as Unit A.

### STOP LINE (Unit B)

No pushes, no PRs, no gate acts. Only these paths:

```
validators/creator_engine_validator/brain_intent_materializer.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_pr_preflight.py
validators/tests/unit/test_brain_intent_materializer_hold.py
.ce/changelog/ce-491-prearming.md
.ce/pr-manifests/ce-491-prearming.md
.ce/wt-491-prearming/READY
.ce/wt-491-prearming/BLOCKED
```

Carrier: slug `ce-491-prearming` exactly; every changed path enumerated; exactly ONE
`- **Declared work class:** T` line.

### READY / BLOCKED signals (Unit B)

**When DONE — write `.ce/wt-491-prearming/READY` then emit to pane:**
```
STATUS: READY
BRANCH: ce-491-prearming
COMMIT: <HEAD SHA after final commit>
CARRIER: .ce/pr-manifests/ce-491-prearming.md
PROBE_ITEM1: <open|already_resolved>
PROBE_ITEM2: <open|already_resolved>
PROBE_ITEM3: <open|already_resolved>
PROBE_ITEM4: <open|already_resolved>
ITEMS_ADDRESSED: <count of items actually changed>
ACTOR_VERSION_NEW: <value or "skipped: already_resolved">
VALIDATE_PR: GREEN
GATE_NOISE: <"none" or verbatim text of external false-RED gates on untouched files>
READY ce-491-prearming <sha> .ce/pr-manifests/ce-491-prearming.md
```
Commit the signal file as the FINAL commit on the branch before stopping.

**When BLOCKED — write `.ce/wt-491-prearming/BLOCKED` then emit:**
```
STATUS: BLOCKED
BRANCH: ce-491-prearming
BLOCKER: <one-sentence description>
CONTEXT: <full context, file/line/error>
BLOCKED ce-491-prearming <reason>
```

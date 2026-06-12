# PR path manifest — ce-ops#26 · seat lifecycle sentinels (push-not-poll)

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref seat-sentinels
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself; `branch_slug("seat-sentinels") == "seat-sentinels"`).

Ratified gate:
Operator-RATIFIED ce-ops#26 gate spec
(`~/projects/ce-ops/designs/ce-26-seat-sentinels-gate-spec-DRAFT-20260612.md`, sha
`86b35959a885cc78a562546a5f0b8585eee4d5b57cdf4476c339c647340bfa76`) — full CE contract
triple (Fork D-1) + launcher wiring + cockpit L2 fold + `events_ref` stamp.

Base:
`309d38dd` (origin/main). Re-ground vs the spec's `570b20cf` pin is a base-only forward
motion (Fork-A pre-authorized + declared), rebased forward in two hops:
- `4878306d` (#208 D3 mcp-fix) — #207 (ce-ops#16 venue/seat spawn hardening) landed the
  `RUNS_SUBDIR` chain layout + the dispatch-record additive-optional keys this gate re-grounds
  onto; #208 reworked `v3_seat_bridge.spawn_seat`'s relative `--mcp-config` argv (this gate's
  `events_ref` stamp composes onto it).
- `309d38dd` — #209 (ce-ops#11-p2 zero-tolerated-failure suite surface) + #210 (v3.1-B.8
  Operator-notify feed, which added the `runner.notify_feed` v3 module → `V3_RUNTIME 35→36` and
  rebuilt the validator wheel). The wheelhouse conflict (both sides rebuilt) was resolved by
  REBUILDING the wheel from THIS rebased source (the combined-wheel rule, pre-authorized) +
  re-pinning `SHA256SUMS` (only the validator-wheel line differs from main; `build/` cleaned).
The §2 grounding holds at this base — counters re-verified V1_RUNTIME==22 / V3_RUNTIME==36
(#210's notify-feed module), registry 52→53.

Counter truth table (re-grounded, §3.6):
- `V1_RUNTIME == 22` — **unchanged** (wiring edits existing members; no new v1 module).
- `V3_RUNTIME == 36` — **unchanged by THIS gate** (the 36 is #210's `runner.notify_feed`;
  `seat_sentinel` is **shared** and `cockpit_readmodel` already a member, so this gate adds no
  runtime module).
- `BASELINE_SHARED_TO_VERSION_ALLOWLIST` — **untouched** (`seat_sentinel` imports no
  version-specific module; the ratchet stays green with zero new entries).
- Check registry `52 → 53` at **8 assertion sites** (Fork D-1 — mechanical, enumerated).

Manifest amendment (§4 sanctioned — "exact test-file homes pinned at execution; if a name
differs the manifest is amended BEFORE work continues"): the launch-path pane-command
assertions also live in `test_lane_runtime_resource_bound.py`,
`test_launch_runtime_resource_bound.py`, and `test_ce_launch_cli.py` — added here because the
sentinel wrapper is now the OUTERMOST pane command (`["/bin/sh", <wrapper>]`) and these tests
recover the bounded inner argv from the generated wrapper (the ordering teeth).

Per-file purpose (the closed path-set — 32 paths):
- **`.ce/pr-manifests/seat-sentinels.md`** *(A)* — this carrier (self-inclusive).
- **`schemas/seat-event.schema.yaml`** *(A)* — the JSONL line schema (versioned day one; the
  `outcome` enum pinned identical to `runtime-evidence.schema.yaml`).
- **`schemas/dispatch-record.schema.yaml`** *(M)* — additive OPTIONAL `events_ref` key on the
  CLOSED schema (`unevaluatedProperties: false`); no new required field; old records validate
  byte-unchanged; re-grounded onto the #16-landed version.
- **`validators/creator_engine_validator/seat_sentinel.py`** *(A)* — the **shared** module:
  constants, the PURE POSIX-sh wrapper builder, `prepare_seat_sentinel`, the tolerant parser,
  `load_seat_events`, the `seat_event` check body, and the `resolve-outcome` CLI.
- **`validators/creator_engine_validator/checks/seat_event.py`** *(A)* — the thin registered
  check (Fork D-1) delegating to `seat_sentinel`.
- **`validators/creator_engine_validator/checks/__init__.py`** *(M)* — register `seat_event`.
- **`validators/creator_engine_validator/lane_runtime.py`** *(M)* — wrap the OUTERMOST
  `launch_command` before `ensure_pane`; `events_ref` on the sidecar + `LaunchResult`.
- **`validators/creator_engine_validator/launch_runtime.py`** *(M)* — seat-surface resolver
  (dispatch-driven seat_id = run_id; bare seat = `<session>--<window>` slug) + wrap before
  `ensure_pane`; `events_ref` on the `--json` `LaunchResult`.
- **`validators/creator_engine_validator/v3_seat_bridge.py`** *(M)* — stamp `events_ref` from
  the v1 `LaunchResult` into `dispatch.yaml` (additive; composes onto #208's relative argv).
- **`validators/creator_engine_validator/runner/cockpit_readmodel.py`** *(M)* —
  `load_seat_events` seam + `_fold_seat_events` + dispatch join by run_id (L2 stays pure JSON;
  `watch_paths` byte-identical).
- **`examples/well-formed/seat-events/events.jsonl`** *(A)* /
  **`examples/malformed/seat-events/events.jsonl`** *(A)* — the CI well-formed-pass /
  malformed-fail corpus.
- **`docs/architecture/seat-sentinel-contract.md`** *(A)* — the convention doc (done-when item).
- **`validators/tests/unit/test_seat_sentinel.py`** *(A)* — contract + real-`/bin/sh`
  silence≠success tests (exit code, SIGKILL→137, trapped TERM/HUP, resolve-outcome, broken
  interpreter, builder purity, enum identity).
- **`validators/tests/unit/test_lane_runtime.py`**, **`test_lane_runtime_reviewer_venue.py`**,
  **`test_launch_runtime.py`**, **`test_v3_seat_bridge.py`**, **`test_cockpit_readmodel.py`**,
  **`test_lane_runtime_resource_bound.py`**, **`test_launch_runtime_resource_bound.py`**,
  **`test_ce_launch_cli.py`** *(M)* — wiring tests (pane cmd == `["/bin/sh", <wrapper>]`;
  inner argv recovered from the wrapper; refusals precede any sentinel side effect; events_ref
  stamp).
- **`validators/tests/unit/test_version_boundary.py`**, **`test_evidence_sink.py`**,
  **`test_redact.py`**, **`test_app_jwt_runner.py`**, **`test_open_change.py`**,
  **`test_merge.py`**, **`test_change_status.py`**, **`test_credential_runner.py`** *(M)* —
  the registry `52 → 53` bump at the 8 assertion sites.
- **`validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl`** *(M)* — wheel
  rebuilt from this branch's source (`validators/creator_engine_validator/**` touched; the
  packaging contract byte-checks bundled `.py` against source; `validators/build` cleaned).
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — re-pinned for the rebuilt wheel.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=32

AUTHORIZED_PATHS_SHA256=e0bdeba9c123f470c205f17c0b2e42864379408fcf6a80e8d5d732568cfdc6f7

```text
.ce/pr-manifests/seat-sentinels.md
docs/architecture/seat-sentinel-contract.md
examples/malformed/seat-events/events.jsonl
examples/well-formed/seat-events/events.jsonl
schemas/dispatch-record.schema.yaml
schemas/seat-event.schema.yaml
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/seat_event.py
validators/creator_engine_validator/lane_runtime.py
validators/creator_engine_validator/launch_runtime.py
validators/creator_engine_validator/runner/cockpit_readmodel.py
validators/creator_engine_validator/seat_sentinel.py
validators/creator_engine_validator/v3_seat_bridge.py
validators/tests/unit/test_app_jwt_runner.py
validators/tests/unit/test_ce_launch_cli.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_cockpit_readmodel.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_evidence_sink.py
validators/tests/unit/test_lane_runtime.py
validators/tests/unit/test_lane_runtime_resource_bound.py
validators/tests/unit/test_lane_runtime_reviewer_venue.py
validators/tests/unit/test_launch_runtime.py
validators/tests/unit/test_launch_runtime_resource_bound.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_redact.py
validators/tests/unit/test_seat_sentinel.py
validators/tests/unit/test_v3_seat_bridge.py
validators/tests/unit/test_version_boundary.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl
```

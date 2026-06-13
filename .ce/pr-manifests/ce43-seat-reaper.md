# PR path manifest — ce43-seat-reaper · ce-ops#43 Automated Seat/Venue Retirement Reaper

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce43-seat-reaper
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

Ratified gate:
Operator-RATIFIED rev-4 gate spec `RATIFIED-SPEC-ce43-rev4.md`
(file sha256 `fc60f564e0283bc495abaf0e608ef8774a519cbcfdfc45248f63242ff33f484f`) on ce-ops#43
(issuecomment-4693658283). Scope `ce43-seat-reaper`, ratified scope sha
`9efd8f0806a1c3549d1866fcce9f70683d04399248fe0285112ed80e21fd1b64`.

Base / re-ground:
Spec pinned at `44b4c71` (#218); current `main` is `20c460c` (#220 v35e-prime-wave +
#221/#222/#224 landed since). The mechanical re-ground was Operator-authorized (path-set
unchanged). Re-verified at this base:
- closed implementation path-set (14 paths) SHA256 still `e710b83a…` — **unchanged**.
- `V1_RUNTIME == 23` (unchanged); `V3_RUNTIME 38 → 40` (the spec's stale "38" was the
  `44b4c71` baseline; #220 already moved it 36 → 38, so this gate's two new V3 modules take
  it to **40**, NOT 38); validator check registry stays **53** (the seat-retirement-record
  schema + its check are DEFERRED to a follow-up per §8 — no registry/check change).
- v1/v3 boundary holds: `seat_reaper` + `reaper_executors` import no v1 module; the two v1
  crossings (`ce lane archive --json`, `creator-engine-validator pco-release`) are
  subprocess+DATA (AST-asserted in `test_version_boundary.py::test_14_*`).

The change (rev-4 MVP):
A substrate-neutral retirement reaper triggered by terminal seat-sentinel events. `seat_reaper`
(V3) folds local state (dispatch records, `events.jsonl`, runtime-evidence chains, ledger
markers, its own NDJSON ledger), classifies each seat deterministically, and orchestrates an
ordered pipeline — archive (verified) → close venue → release worktree/markers → record —
delegating every irreversible action to a per-substrate executor. `reaper_executors` (V3) ships
the tmux executor, crossing to the v1 transcript-archive + `pco-release` legs as subprocess+DATA
and verifying the JSON/filesystem facts; an unknown substrate yields no executor (the policy
escalates). The reaper **re-implements** the seat-sentinel outcome resolution READ-ONLY (it never
calls `resolve_outcome`, which would append an event). Unclean/stale/unknown stops fail closed to
the existing escalation queue (B.8-bannerable); a `conserve` marker is an absolute teardown stop.
`cev3 reap once|watch|status` follows the `notify` I/O-edge daemon house style (JSON action names
`reap_once` / `reap_watch_tick` / `reap_status`); status + the eval phase of once/watch write
nothing and leave `events.jsonl` byte-identical.

Per-file purpose (the closed path-set — 17 paths = 14 implementation + this carrier + 2 orchestrator-rebuilt wheelhouse artifacts):
- **`.ce/pr-manifests/ce43-seat-reaper.md`** *(A)* — this carrier (self-inclusive).
- **`docs/operations/SEAT_REAPER_PROTOCOL.md`** *(A)* — the prose contract (done-when doc).
- **`schemas/dispatch-record.schema.yaml`** *(M)* — additive OPTIONAL conserved-evidence marker
  (`conserve` / `conserve_reason` / `conserved_at`) on the CLOSED schema
  (`unevaluatedProperties: false`); old records validate byte-unchanged.
- **`validators/creator_engine_validator/_versions.py`** *(M)* — classify `seat_reaper` +
  `reaper_executors` as V3_RUNTIME (38 → 40).
- **`validators/creator_engine_validator/seat_reaper.py`** *(A)* — the substrate-neutral policy:
  discovery, deterministic classification, read-only outcome resolution, escalation emission
  (deterministic ids, deduped), the ordered pipeline, the private NDJSON ledger, honest counters,
  `reap_status` / `reap_once`.
- **`validators/creator_engine_validator/reaper_executors.py`** *(A)* — the tmux executor
  (transcript archive via `ce lane archive --json`; pane kill + verify + pane-registry close;
  worktree/ledger release via `pco-release` + verification) and the substrate selector.
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* — `cev3 reap once|watch|status`
  (notify house style; SIGINT/SIGTERM stop the watch loop cleanly after the current pass).
- **`validators/tests/unit/test_seat_reaper.py`** *(A)* — §10 ratification tests at the policy
  layer (clean-terminal-reaps, never-reaps-conserved, unclean-stop-escalates,
  evidence-chain-folds, unresolvable-past-grace, archive-before-remove-ordering,
  failed-spawn-archive-conserve, root-checkout-refusal, idempotent-once, unknown-substrate) +
  determinism / read-only-resolution / dedup.
- **`validators/tests/unit/test_v3_cli.py`** *(M)* — `reap` CLI: required JSON shapes,
  status-is-read-only (events.jsonl byte-identical, no writes), watch-tick-shape + clean
  SIGINT/SIGTERM stop, invalid-interval refusal.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* — `V3_RUNTIME == 40`; classify the
  two modules V3; §10.14 v3-boundary-holds (AST: no v1 import; subprocess+DATA crossings).
- **`validators/tests/integration/test_pco_allocator_cli.py`** *(M)* — §10.8 pco-release-leg-is-
  reused: the executor drives the REAL `creator-engine-validator pco-release` CLI against a temp
  secondary worktree, verifying claim release / lease removal / `claim_released` event / worktree
  removal WITHOUT branch deletion; + root-checkout refusal surfacing.
- **`validators/tests/unit/test_pane_registry.py`** *(M)* — the executor's pane-registry close
  step (closed/completed + aborted/aborted, schema-valid, identity preserved; write-failure flag).
- **`validators/tests/unit/test_pco_allocator.py`** *(M)* — the executor's pco-release reuse
  (argv + mapped release reason; not-applicable without binding; already-satisfied skip; root
  refusal flag).
- **`validators/tests/unit/test_transcript_archive.py`** *(M)* — the executor's archive leg
  (`ce lane archive --json` argv + JSON consumption; session-id / codex-ref resolution;
  missing-when-expected failure; ambiguous refusal).
- **`validators/tests/unit/test_v3_seat_bridge.py`** *(M)* — the conserved-evidence marker
  validates against the (additively-extended, still-closed) dispatch schema.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* — the committed
  app wheel, rebuilt by the orchestrator from this branch's source so the packaging-contract guard
  (`verify_wheel_matches_source`) sees the two new V3 modules + the `_versions.py`/`v3_cli.py` deltas
  byte-identical (sha256 `88fac613…`).
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — re-pinned app-wheel digest (only that line changed;
  the 6 dependency wheels are byte-unchanged).

Posture: the seat committed LOCALLY only — NO `git push`, NO `gh pr`, NO merge. The orchestrator
then rebuilt the committed app wheel from this branch's source + re-pinned
`validators/wheelhouse/SHA256SUMS` (the +2 wheelhouse paths above; app wheel sha256 `88fac613…`)
in a separate commit, then pushes; the Operator merges.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=17

AUTHORIZED_PATHS_SHA256=98a95405d266e4950e814684a408f7bf9e5e934b6b91c0c9229069bba54ca75d

```text
.ce/pr-manifests/ce43-seat-reaper.md
docs/operations/SEAT_REAPER_PROTOCOL.md
schemas/dispatch-record.schema.yaml
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/reaper_executors.py
validators/creator_engine_validator/seat_reaper.py
validators/creator_engine_validator/v3_cli.py
validators/tests/integration/test_pco_allocator_cli.py
validators/tests/unit/test_pane_registry.py
validators/tests/unit/test_pco_allocator.py
validators/tests/unit/test_seat_reaper.py
validators/tests/unit/test_transcript_archive.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_seat_bridge.py
validators/tests/unit/test_version_boundary.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```

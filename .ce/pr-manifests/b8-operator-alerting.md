# PR path manifest — ce-ops#31 · v3.1-B.8 Operator-notify feed (the AWAITING-OPERATOR detection layer)

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref b8-operator-alerting
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

Ratified gate:
Operator-RATIFIED ce-ops#31 Tier-1 gate spec
(`designs/ce-31-operator-alerting-gate-spec-DRAFT-20260612.md`, ratified as written, sha
`a3255925a9b210659e56e2f02ab6c3d05fe7586ffb2de7f081fa744cf1bdc77e`); ratified Scope
`b8-operator-alerting` (`ratified_scope_sha 858ba93e…`, `approver_ref a3255925…`). The
combined-source wheel rebuild + `SHA256SUMS` re-pin is pre-authorized by the ratification
(§3.1/§4 — `runner.notify_feed` is wheel-shipped; the packaging contract byte-checks the
bundled `.py` against source).

Base:
`4878306de4642a9126370607849e5b28143ebe4c` (origin/main = #208, the D3 mcp-fix). The spec
named re-ground pin `3bdc129c` (#207); main moved to `4878306d` by the #208 base-only
motion (Fork-A pre-authorized + declared by the orchestrator) — a content-pin-unchanged
base refresh under [[ce-base-only-refresh-microauth]], path-set otherwise untouched. The §7
re-ground confirmed ce-ops#21 has MERGED (#206) → this carrier IS the post-#21 per-PR form
(A, self-inclusive); the retired shared `.ce/pr-path-manifest.md` is absent from this diff.
The §2 grounding line-anchors hold at this base. The §4 row #2 flips the B.7 roadmap row
`LANDING → MERGED #204/570b20c` (same H-6 pattern, spec-authorized) — no other LANDING row
touched.

Per-file purpose (the closed path-set — 10 paths, as ratified §4; carrier in per-PR form):
- **`.ce/pr-manifests/b8-operator-alerting.md`** *(A)* — this carrier (self-inclusive).
- **`docs/architecture/cockpit.md`** *(M)* — the "Operator alerting (v3.1-B.8)" section:
  the ledger-as-memory adjudication, config format, sink contract, payload modes, surface.
- **`docs/v3-roadmap.md`** *(M)* — the v3.1-B.8 gate-status row (+ B.7 `LANDING → MERGED`
  `#204/570b20c`).
- **`validators/creator_engine_validator/_versions.py`** *(M)* — `runner.notify_feed` added
  to `V3_RUNTIME` (35 → 36) with a justifying comment.
- **`validators/creator_engine_validator/runner/notify_feed.py`** *(A)* — the module: PURE
  `fold_notify_feed` + `shape_payload` + `parse_notify_config` (config validation, incl. the
  loud `digest` refusal) + the narrow I/O edges (`load_ledger`/`append_delivery`/`load_config`
  + `dispatch_desktop`/`dispatch_exec` + the `run_once` composition root). REUSES
  `cockpit_readmodel.load_escalations`; imports no `textual`/v1 module (AST-asserted).
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* — `notify once|watch|status`
  wiring (`_cmd_notify` + family, parser, `_DISPATCH` entry); `--sync-repo/--sync-label` reuse
  of the existing `escalation sync` legs for cross-host fan-in; lazy notify_feed import
  (principle-6 routing).
- **`validators/tests/unit/test_notify_feed.py`** *(A)* — §6 tests: the pure-fold matrix,
  payload key-absence, config validation incl. `digest` refusal, the desktop/exec sinks
  (fake runner), `run_once` ledger durability + idempotency, the `notify once|status` CLI +
  the sync leg (stubbed gh runner, sync-failure-tolerated), and the boundary/no-v1-import
  invariants.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* — the `V3_RUNTIME` count
  assertion 35 → 36, co-moved same-commit (registry 52 unchanged).
- **`validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl`** *(M)* — the
  wheel rebuilt from this branch's source (`runner.notify_feed` is wheel-shipped; the
  packaging contract byte-checks bundled `.py` against source).
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — re-pinned for the rebuilt wheel.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=49a70560049264c4e5de38b74e7e65e6aedc23bf15c8d3e7f6b36fdde4b9ac24

```text
.ce/pr-manifests/b8-operator-alerting.md
docs/architecture/cockpit.md
docs/v3-roadmap.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/runner/notify_feed.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_notify_feed.py
validators/tests/unit/test_version_boundary.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl
```

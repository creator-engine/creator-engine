# PR path manifest — G1-codex · `cev3 drive --harness codex`

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref codex-drive-bridge
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

Ratified gate:
Operator-ratified G1-codex gate spec rev-2
(`/home/ce/projects/ce-ops/designs/ce-codex-drive-bridge-gate-spec-DRAFT-20260612.md`,
sha256 `a4b84b3c8f213a98186261a89667cf002836a1a361ae7beebaa2b078d62b10db`).

Base:
`ce25fe59cefde080a40330035b3ad2c28f5455b8` (branch `codex-drive-bridge`, current main
at handoff). The rev-2 citation recheck at this base found only mechanical line-anchor drift
already named in the spec amendment; no non-mechanical drift was accepted.

Scope adjudication:
IN: explicit `cev3 drive --spawn --harness codex` for low-risk Scope classes; high-risk
Codex drive only with value-free `--codex-risk-override <HEX64>`; v1 Codex `CDX-D-*`
launch-spec refusals; ambient GitHub credential scrub; Codex transcript locator stamping
before live projection; harness-keyed collect resolution with spawn-stamped `transcript_ref`
primary and `~/.codex/sessions/` exact-key fallback; dispatch schema widening; `V1_RUNTIME`
22->23; focused tests and integration dry-run coverage; branch-source wheel rebuild.

OUT: auto-routing; live Codex hook-pack; Ring-1 parity claims; Codex reviewer venue migration;
semantic changes to `cev3 pr`, `cev3 review`, or `cev3 merge`.

Per-file purpose:
- **`.ce/pr-manifests/codex-drive-bridge.md`** *(A)* — this carrier (self-inclusive).
- **`validators/creator_engine_validator/codex_launch_spec.py`** *(A)* — CDX-D Ring-0
  Codex launch-spec parser/evaluator/builder; refuses unsafe surfaces and builds the
  credential-scrubbing `env -u ... codex` command.
- **`validators/creator_engine_validator/_versions.py`** *(M)* — classifies
  `codex_launch_spec` as v1 runtime; `V1_RUNTIME` count moves 22 -> 23.
- **`validators/creator_engine_validator/launch_runtime.py`** *(M)* — governed Codex
  branch in `ce launch`, Codex bypass-mode stamp, CDX-D refusal surfacing, resource-bound
  wrapper preserved after Ring 0.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* — `--codex-arg` on `ce launch`
  and `ce hud`, with harness-specific extra-arg routing.
- **`validators/creator_engine_validator/v3_seat_bridge.py`** *(M)* — harness registry,
  Codex dispatch materialization, Codex launch argv composition, transcript snapshot/poll/stamp
  helpers, and conserved Claude reviewer venue behavior.
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* — Codex drive risk guard and
  override recording, harness-keyed collect resolver, parser help, and Codex review deferral.
- **`schemas/dispatch-record.schema.yaml`** *(M)* — widened harness enum and optional
  `harness_session_id`, `transcript_ref`, `harness_boundary`, `codex_bypass_mode`, and
  `codex_risk_override` fields; value-free constraints conserved.
- **`docs/v3-roadmap.md`** *(M)* — G1-codex LANDING row, conserving the
  externally-gate-governed/no-Ring-1-parity labeling and Codex reviewer venue deferral.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* — V1 runtime counter update.
- **`validators/tests/unit/test_codex_launch_spec.py`** *(A)* — CDX-D clause tests.
- **`validators/tests/unit/test_launch_runtime.py`** *(M)* — governed Codex command,
  unsafe Codex refusal, and CLI-arg isolation coverage.
- **`validators/tests/unit/test_launch_runtime_resource_bound.py`** *(M)* — mechanical
  update to assert the existing resource-bound wrapper encloses the governed Codex command
  built by CDX-D Ring 0.
- **`validators/tests/unit/test_ce_launch_cli.py`** *(M)* — `--codex-arg` dry-run JSON and
  allowlist-refusal coverage.
- **`validators/tests/unit/test_v3_seat_bridge.py`** *(M)* — Codex registry/dispatch,
  launch argv, transcript locator success/failure coverage.
- **`validators/tests/unit/test_v3_cli.py`** *(M)* — Codex low/high-risk drive guard,
  override recording, review deferral, and collect transcript resolution coverage.
- **`validators/tests/integration/test_ce_launch_cli.py`** *(M)* — side-effect-free Codex
  dry-run integration coverage.
- **`validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl`** *(M)* —
  rebuilt from this branch's source.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — re-pinned for the rebuilt wheel.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=19

AUTHORIZED_PATHS_SHA256=7ade20ca6cac490e3a89316d10e4bebd046c155fe2a6bc738998c4f2a6de1ad4

```text
.ce/pr-manifests/codex-drive-bridge.md
docs/v3-roadmap.md
schemas/dispatch-record.schema.yaml
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/codex_launch_spec.py
validators/creator_engine_validator/launch_runtime.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_seat_bridge.py
validators/tests/integration/test_ce_launch_cli.py
validators/tests/unit/test_ce_launch_cli.py
validators/tests/unit/test_codex_launch_spec.py
validators/tests/unit/test_launch_runtime.py
validators/tests/unit/test_launch_runtime_resource_bound.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_seat_bridge.py
validators/tests/unit/test_version_boundary.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl
```

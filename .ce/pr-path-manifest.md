# PR path manifest - v3.1-G1 live-spawn gate

CI passes this to `verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; the
fidelity scan requires the declared count and SHA256 to match the fenced block.

Ratified gate:
`~/ce-launch/v31-g1-wave/v31-g1-live-spawn-gate-RATIFIED-20260611.md`
(sha256 `c5439f4fa89c90e6cb30a4367ccdbb384d83d95e811d163c787e514eefae4a5c`;
Operator-ratified 2026-06-11, Section 6 fork resolutions binding).

Implementer mandate:
`~/ce-launch/v31-g1-wave/G1_IMPL_MANDATE.md`.

Per-file purpose (the closed 15-row manifest — two serial gates, one branch):
- **`validators/creator_engine_validator/v3_seat_bridge.py`** *(NEW)* - G1a: the assemble→spawn
  bridge (`materialize_dispatch` / `spawn_seat` / `seed_brief`); crosses to the v1 launcher as
  subprocess + DATA only, importing NO v1 module.
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* - G1a `drive --spawn` (additive opt-in
  + `--no-unattended` + non-claude refusal) + G1b `collect` evidence fold + status/report/artifacts
  read-model wiring.
- **`validators/creator_engine_validator/launch_runtime.py`** *(M)* - G1a defect-a: provision the
  strict MCP config before the tmux spawn (reusing the lane helper; exception → `LaunchRefused`).
- **`validators/creator_engine_validator/lane_runtime.py`** *(M)* - G1a: promote
  `_ensure_lane_mcp_config` to public `ensure_lane_mcp_config` (deprecation alias kept).
- **`validators/creator_engine_validator/_versions.py`** *(M)* - G1a `V3_RUNTIME` += `v3_seat_bridge`
  (32→33) + G1b `V3_SCHEMAS` += `dispatch-record.schema.yaml` (4→5).
- **`schemas/dispatch-record.schema.yaml`** *(NEW)* - G1b: the value-free dispatch-record shape.
- **`validators/tests/unit/test_v3_seat_bridge.py`** *(NEW)* - G1a+G1b: the bridge unit suite,
  including the AST no-v1-import invariant + the schema-conformance test.
- **`validators/tests/unit/test_v3_cli.py`** *(M)* - G1a+G1b: `drive --spawn` / `collect` / read-model
  + the end-to-end faked-seam keystone test.
- **`validators/tests/unit/test_launch_runtime.py`** *(M)* - G1a: defect-a MCP provisioning + defect-b
  CC-D-6 unattended-flag tests.
- **`validators/tests/unit/test_lane_runtime.py`** *(M)* - G1a: the helper rename + alias tests.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - G1a: `len(V3_RUNTIME)` 32→33 (ships in
  the same commit as the `_versions.py` baseline edit).
- **`validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl`** *(M)* - landing: app
  wheel rebuilt ONCE from the combined branch source.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - landing: re-pinned for the rebuilt app wheel.
- **`docs/v3-roadmap.md`** *(M)* - landing: the v3.1-G1 row in the gate-status table.
- **`.ce/pr-path-manifest.md`** *(M)* - this carrier.

- **base:** `c3dcae0a3dc8793a9ebf601fe1d5539af9aa0141` (origin/main post-#197, per mandate).
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=15

AUTHORIZED_PATHS_SHA256=a7b2ed86bef96ff21f3cce58f41649bcb3b57bbf5748b1f9b0f85a4c01165e15

```text
.ce/pr-path-manifest.md
docs/v3-roadmap.md
schemas/dispatch-record.schema.yaml
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/lane_runtime.py
validators/creator_engine_validator/launch_runtime.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_seat_bridge.py
validators/tests/unit/test_lane_runtime.py
validators/tests/unit/test_launch_runtime.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_seat_bridge.py
validators/tests/unit/test_version_boundary.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl
```

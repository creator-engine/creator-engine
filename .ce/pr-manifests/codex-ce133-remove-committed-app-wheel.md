# PR path manifest - codex-ce133-remove-committed-app-wheel

ce-ops#133 / night arc #170 implementation of ADR-0006 Gate 3: remove the
committed development first-party app wheel, keep the dependency wheelhouse
checked, and replace committed-wheel parity with source-built wheel parity.

Base:
`6e2e697063d98b526398e8418904be6ec05a8a65` (`origin/main` at rebase).

Per-file purpose:

- **`.ce/changelog/ce133-remove-committed-app-wheel.md`** *(A)* - changelog
  fragment for the Gate 3 removal slice.
- **`.ce/pr-manifests/codex-ce133-remove-committed-app-wheel.md`** *(A)* - this
  self-inclusive carrier.
- **`README.md`** *(M)* - clarifies clone mode uses dependency wheels plus
  `PYTHONPATH=validators`.
- **`docs/architecture/ADR-0006-derived-artifacts-out-of-trust-path.md`** *(M)* -
  records Gate 3 implementation status.
- **`docs/decisions/ADR-0010-take-app-wheel-out-of-authored-prs.md`** *(M)* -
  records the removal implementation note while leaving public release path
  unchanged.
- **`docs/guide/contributing-to-ce.md`** *(M)* - updates contributor clone-mode
  install guidance.
- **`docs/operations/AGENT_NATIVE_BOOTSTRAP.md`** *(M)* - updates source-backed
  bootstrap/preflight/install commands.
- **`docs/operations/V1_DELIVERY_REHEARSAL.md`** *(M)* - updates rehearsal
  clone-mode install guidance.
- **`templates/hermes/agent-native-bootstrap.yaml`** *(M)* - switches bootstrap
  commands to dependency install plus `PYTHONPATH` source execution.
- **`validators/README.md`** *(M)* - documents dependency-only runtime
  wheelhouse posture.
- **`validators/creator_engine_validator/_version.py`** *(M)* - refreshes the
  baked build SHA to the rebased main merge-parent.
- **`validators/creator_engine_validator/brain_probe.py`** *(M)* - reuses the
  packaging runtime source-build parity checker.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - updates doctor
  packaging help text.
- **`validators/creator_engine_validator/doctor_runtime.py`** *(M)* - surfaces
  dependency wheelhouse and committed app-wheel posture in doctor JSON.
- **`validators/creator_engine_validator/environment_guard.py`** *(M)* - updates
  RED-G-6 wording to dependency wheelhouse.
- **`validators/creator_engine_validator/packaging_runtime.py`** *(M)* - forbids
  committed app wheels in `validators/wheelhouse` and builds first-party parity
  wheels from source.
- **`validators/tests/integration/test_ce_doctor_cli.py`** *(M)* - covers doctor
  JSON and bootstrap template posture.
- **`validators/tests/unit/test_ce_doctor_cli.py`** *(M)* - covers doctor JSON
  posture fields.
- **`validators/tests/unit/test_packaging_contract.py`** *(M)* - covers
  dependency-only wheelhouse and source-built wheel parity behavior.
- **`validators/tests/unit/test_wheel_bake.py`** *(M)* - updates wheel bake
  helper expectations for no committed app wheel.
- **`validators/tests/unit/test_wheelhouse_built_surface.py`** *(M)* - builds a
  temporary source wheel for surface parity.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - removes the first-party app
  wheel digest line only.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`**
  *(D)* - removes the committed development first-party app wheel.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=23

AUTHORIZED_PATHS_SHA256=cf4e1031297af06c740793df91cef7a2cb146fb78a93a78da9933119189ad7b4

```text
.ce/changelog/ce133-remove-committed-app-wheel.md
.ce/pr-manifests/codex-ce133-remove-committed-app-wheel.md
README.md
docs/architecture/ADR-0006-derived-artifacts-out-of-trust-path.md
docs/decisions/ADR-0010-take-app-wheel-out-of-authored-prs.md
docs/guide/contributing-to-ce.md
docs/operations/AGENT_NATIVE_BOOTSTRAP.md
docs/operations/V1_DELIVERY_REHEARSAL.md
templates/hermes/agent-native-bootstrap.yaml
validators/README.md
validators/creator_engine_validator/_version.py
validators/creator_engine_validator/brain_probe.py
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/doctor_runtime.py
validators/creator_engine_validator/environment_guard.py
validators/creator_engine_validator/packaging_runtime.py
validators/tests/integration/test_ce_doctor_cli.py
validators/tests/unit/test_ce_doctor_cli.py
validators/tests/unit/test_packaging_contract.py
validators/tests/unit/test_wheel_bake.py
validators/tests/unit/test_wheelhouse_built_surface.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```

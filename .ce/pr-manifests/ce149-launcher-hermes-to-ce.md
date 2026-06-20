# PR path manifest - ce149-launcher-hermes-to-ce

Design/task: `creator-engine/ce-ops#149`.

Base:
`28e571119aa42e8d732961c2e2e4d6fb6bb51297`

This is the closed path set for the launch-path-only migration from reserved
`.hermes/` state to canonical `.ce/state` state. It intentionally excludes the
broader deferred v1 `.hermes` rename/freeze.

Per-file purpose:

- **`.ce/changelog/ce149-launcher-hermes-to-ce.md`** *(A)* - per-change changelog fragment.
- **`.ce/pr-manifests/ce149-launcher-hermes-to-ce.md`** *(A)* - this PR's closed path-set carrier.
- **`docs/contracts/v3-naming-hygiene.md`** *(M)* - contract note for the launch-surface hygiene exception.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - top-level `ce launch`/`ce hud` help text for `.ce/state` defaults.
- **`validators/creator_engine_validator/checks/v3_naming_hygiene.py`** *(M)* - launch-surface `.hermes` residue scan.
- **`validators/creator_engine_validator/launch_runtime.py`** *(M)* - launch MCP config and lifecycle ledger defaults under `.ce/state`.
- **`validators/tests/unit/test_ce_launch_cli.py`** *(M)* - CLI help regression.
- **`validators/tests/unit/test_launch_runtime.py`** *(M)* - launch default regression coverage.
- **`validators/tests/unit/test_v3_naming_hygiene.py`** *(M)* - planted launch-surface residue regression.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - refreshed digest for the rebuilt app wheel.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - rebuilt app wheel for source parity.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=11

AUTHORIZED_PATHS_SHA256=5289208a792599c348b07597758c45fbf0ffd766078325aec2511ae0e2694ce6

```text
.ce/changelog/ce149-launcher-hermes-to-ce.md
.ce/pr-manifests/ce149-launcher-hermes-to-ce.md
docs/contracts/v3-naming-hygiene.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/checks/v3_naming_hygiene.py
validators/creator_engine_validator/launch_runtime.py
validators/tests/unit/test_ce_launch_cli.py
validators/tests/unit/test_launch_runtime.py
validators/tests/unit/test_v3_naming_hygiene.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```

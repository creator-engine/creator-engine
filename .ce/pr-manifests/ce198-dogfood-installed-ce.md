# PR path manifest - ce-ops#198 - installed CE dogfood entrypoints

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce198-dogfood-installed-ce --require-carrier

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

- **Declared work class:** feature

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=14

AUTHORIZED_PATHS_SHA256=864fc3c1848bfcf16b05352fbbb9add8007289c5f1c824e427242f2dd7bda4f5

```text
.ce/changelog/ce198-dogfood-installed-ce.md
.ce/pr-manifests/ce198-dogfood-installed-ce.md
deploy/systemd/ce-integrator-daemon.service
deploy/systemd/ce-review-pickup-daemon.service
docs/operations/INSTALLED_CE_DOGFOOD_MIGRATION.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/doctor_runtime.py
validators/creator_engine_validator/environment_guard.py
validators/creator_engine_validator/packaging_runtime.py
validators/creator_engine_validator/pickup.py
validators/tests/unit/test_ce_doctor_cli.py
validators/tests/unit/test_gate_daemons_systemd.py
validators/tests/unit/test_packaging_contract.py
validators/tests/unit/test_pickup.py
```

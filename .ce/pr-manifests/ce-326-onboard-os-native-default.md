# PR path manifest - ce-ops#326 · onboard os-native no-profile default

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-326-onboard-os-native-default` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=bcf1cf2c6fc3e1e84f84a2c5bbad8f566c0fc38f615a934eed27acfddda71d3f

```text
.ce/changelog/ce-326-onboard-os-native-default.md
.ce/pr-manifests/ce-326-onboard-os-native-default.md
validators/creator_engine_validator/onboard_apply.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_installer.py
validators/tests/unit/test_ce_doctor_cli.py
validators/tests/unit/test_onboard_apply.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_installer.py
```

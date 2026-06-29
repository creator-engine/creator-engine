# PR path manifest — ce-ops#353 · OS-native selectability fail-closed fix

- **Declared work class:** story

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-353-osnative-selectability` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=9810a857cb6e0ecaeafc651bd6c044eccf43081a4d67ae4324398a521cf75a73

```text
.ce/changelog/ce-353-osnative-selectability.md
.ce/pr-manifests/ce-353-osnative-selectability.md
docs/design/oq1-os-native-sandbox-mechanism.md
validators/creator_engine_validator/onboard_apply.py
validators/creator_engine_validator/runner/__init__.py
validators/creator_engine_validator/runner/os_native_backend.py
validators/tests/unit/test_onboard_apply.py
validators/tests/unit/test_orchestrator.py
validators/tests/unit/test_runner_backend.py
```

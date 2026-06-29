# PR path manifest — ce-ops#353 · Tranche-2 OS-native sandbox execution fail-closed

- **Declared work class:** feature

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-353-tranche2-osnative-exec-harvest` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=67640dea17c1086d0c5ba4bb18b4e8e13df0e437c2048c8de55a76a8dc59bd87

```text
.ce/changelog/ce-353-tranche2-osnative-exec-harvest.md
.ce/pr-manifests/ce-353-tranche2-osnative-exec-harvest.md
validators/creator_engine_validator/runner/os_native_backend.py
validators/tests/unit/test_orchestrator.py
validators/tests/unit/test_os_native_backend.py
validators/tests/unit/test_runner_backend.py
```

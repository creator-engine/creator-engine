# PR path manifest — ce-ops#368 · CE-native test-coupling validate-pr gate

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-368-test-coupling-gate` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=5e70f80aad88d12b3d352ba09e7df1e0339b54e9bf3fcced9c0ec87376d2deba

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-368-test-coupling-gate.md
.ce/pr-manifests/ce-368-test-coupling-gate.md
.github/workflows/validate.yml
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/test_coupling.py
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_test_coupling.py
```

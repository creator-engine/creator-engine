# PR path manifest — ce-ops#447 · Deduplicate Docker runner translation helpers

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-runner-helper-dedup` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=e84f48417fe2ab5fd9d8cc5a2afa24e8480129304be0bdf5946e9975cc2689f7

```text
.ce/changelog/ce-runner-helper-dedup.md
.ce/pr-manifests/ce-runner-helper-dedup.md
validators/creator_engine_validator/runner/__init__.py
validators/creator_engine_validator/runner/docker_backend.py
validators/creator_engine_validator/runner/gvisor_proxy_backend.py
validators/creator_engine_validator/runner/translation.py
validators/tests/unit/test_runner_translation_helpers.py
```

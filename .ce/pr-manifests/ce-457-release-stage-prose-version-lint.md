# PR path manifest — ce-ops#457 · release-stage prose version lint

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-457-release-stage-prose-version-lint` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=060987e155bdb35e304218ce0ff43e2cdc58df81e00b0508e6ccf1375eaaba05

```text
.ce/changelog/ce-457-release-stage-prose-version-lint.md
.ce/pr-manifests/ce-457-release-stage-prose-version-lint.md
validators/creator_engine_validator/release_publish.py
validators/tests/unit/test_release_publish.py
```

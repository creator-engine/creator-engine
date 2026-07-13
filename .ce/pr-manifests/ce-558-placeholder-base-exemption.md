# PR path manifest — ce-ops#558 · Exempt unresolved placeholder Docker image bases

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-558-placeholder-base-exemption` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=4548f9d023b9838280ac863df4c905459c7e5737faed592d3c0c5dca7536be03

```text
.ce/changelog/ce-558-placeholder-base-exemption.md
.ce/pr-manifests/ce-558-placeholder-base-exemption.md
validators/creator_engine_validator/image_build_smoke.py
validators/tests/unit/test_image_build_smoke.py
```

# PR path manifest — ce-ops#437 · Publish canonical multi-arch runtime image

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-437-s4-runtime-image` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** M

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=601017ef1c23787f39586f803ee485d3fa8557ca54b3f27f2455c0f3ac39c197

```text
.ce/changelog/ce-437-s4-runtime-image.md
.ce/pr-manifests/ce-437-s4-runtime-image.md
.github/workflows/publish-runtime-image.yml
deploy/runtime-image/Dockerfile
deploy/runtime-image/README.md
validators/tests/unit/test_runtime_image.py
```

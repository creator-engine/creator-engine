# PR path manifest — ce-ops#543 · Exempt local Docker image bases from Buildx smoke checks

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-543-local-base-exemption` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=c6fff6ffa69ce4f3b5f44125e41c8a8b20be4325f5526c58c2cb310fdc31cc00

```text
.ce/changelog/ce-543-local-base-exemption.md
.ce/pr-manifests/ce-543-local-base-exemption.md
validators/creator_engine_validator/image_build_smoke.py
validators/tests/unit/test_image_build_smoke.py
```

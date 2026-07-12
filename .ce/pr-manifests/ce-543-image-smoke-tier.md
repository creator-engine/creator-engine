# PR path manifest — ce-ops#543 · Dockerfile image-build smoke tier

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-543-image-smoke-tier` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

BASE=2d7c4635e3c6485eb025f7b4bee540417496901c

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=1d45bfe43660a42e32ccb955582f69057d8629112ebb7b13558575b9bd003bbc

```text
.ce/changelog/ce-543-image-smoke-tier.md
.ce/pr-manifests/ce-543-image-smoke-tier.md
.github/workflows/validate.yml
validators/creator_engine_validator/image_build_smoke.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_image_build_smoke.py
validators/tests/unit/test_pr_preflight.py
```

# PR path manifest — none · fix(install): sync docs/schemas install-answers mirror to canonical + parity guard

- **Declared work class:** story

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-install-schema-mirror-sync` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=96e1604266b070c01c268fbe449d4b6488670337a1d3f9e7bb63a7c61e359ab5

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-install-schema-mirror-sync.md
.ce/pr-manifests/ce-install-schema-mirror-sync.md
docs/schemas/install-answers.schema.yaml
validators/tests/integration/test_install_bootstrap.py
```

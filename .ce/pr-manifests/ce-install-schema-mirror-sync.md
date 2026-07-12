# PR path manifest — none · fix(install): sync docs/schemas install-answers mirror to canonical + parity guard

- **Declared work class:** story

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-install-schema-mirror-sync` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=92d529b79deda4943a343b27a0896333d17d6553b23546e05609bd545246c8f7

```text
.ce/changelog/ce-install-schema-mirror-sync.md
.ce/pr-manifests/ce-install-schema-mirror-sync.md
docs/schemas/install-answers.schema.yaml
validators/tests/integration/test_install_bootstrap.py
```

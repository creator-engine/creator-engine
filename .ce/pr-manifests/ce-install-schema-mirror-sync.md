# PR path manifest — none · fix(install): sync docs/schemas install-answers mirror to canonical + parity guard

- **Declared work class:** story

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-install-schema-mirror-sync` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=a2548bf5d5a401d1fed03ceeb797c4abd7d59fe6a69c615517a38d3e09550cfc

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-install-schema-mirror-sync.md
.ce/pr-manifests/ce-install-schema-mirror-sync.md
docs/schemas/install-answers.schema.yaml
validators/tests/integration/test_install_bootstrap.py
validators/tests/unit/test_ce_brain_drift.py
```

# PR path manifest — ce-ops#358 · Re-sign llms-install.md install spec with ce-root-v1

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref resign-llms-install-spec` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=da9992e9a8c763b267ed10563523ade9c14f8d998fef80033789cdc41d0a11ba

```text
.ce/changelog/resign-llms-install-spec.md
.ce/pr-manifests/resign-llms-install-spec.md
docs/llms-install.md
```

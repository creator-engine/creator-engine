# PR path manifest — ce-ops#360 · Harvest: expand support-agent zero-leak eval corpus

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-supportagent-eval-corpus-expand-harvest` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=2

AUTHORIZED_PATHS_SHA256=df4c7a8e0d27cb52a6412aed3cdba0709e0e19fed41c454fbc82c19ba5b2238b

```text
.ce/changelog/ce-supportagent-eval-corpus-expand-harvest.md
.ce/pr-manifests/ce-supportagent-eval-corpus-expand-harvest.md
```

# PR path manifest — ce-ops#247 · validate the approval-capability merge gate end-to-end

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-wall-armed-demo` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=2

AUTHORIZED_PATHS_SHA256=7c1d9af84b44214871cedb8da0b99b7908be3fed1923c0bbb5bcf8c257d50b9b

```text
.ce/changelog/ce-wall-armed-demo.md
.ce/pr-manifests/ce-wall-armed-demo.md
```

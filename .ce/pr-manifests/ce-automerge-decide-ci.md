# PR path manifest — ce-ops#313 · advisory automerge decision CI

- **Declared work class:** story

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-automerge-decide-ci` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=8eb9f9c5592128847f1932f623dc22152eacff132bfb6d1c8ea24cc5ab12da15

```text
.ce/changelog/ce-automerge-decide-ci.md
.ce/pr-manifests/ce-automerge-decide-ci.md
.github/workflows/automerge-decide.yml
```

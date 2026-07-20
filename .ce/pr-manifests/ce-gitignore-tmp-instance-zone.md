# PR path manifest — ce-ops#635 · ignore repo-root `tmp/` instance zone

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-gitignore-tmp-instance-zone` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** XS

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=fa5e82e22fddc2d42e5c0f924f9f91936ab3288d7e5fe756222381909480b0e5

```text
.ce/changelog/ce-gitignore-tmp-instance-zone.md
.ce/pr-manifests/ce-gitignore-tmp-instance-zone.md
.gitignore
```

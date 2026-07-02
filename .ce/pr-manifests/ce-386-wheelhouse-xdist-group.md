# PR path manifest — ce-ops#386 · Serialize wheelhouse built-surface tests under xdist

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-386-wheelhouse-xdist-group` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=3226f4dba7009e545431f50227f228f67bd7e6c736131e0a9675ec1b3f43f889

```text
.ce/changelog/ce-386-wheelhouse-xdist-group.md
.ce/pr-manifests/ce-386-wheelhouse-xdist-group.md
validators/tests/unit/test_wheelhouse_built_surface.py
```

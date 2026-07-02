# PR path manifest — ce-ops#386 · Serialize wheelhouse built-surface wheel builds under xdist

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-386-xdist-wheelbuild` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** XS

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=53d355fce76e61093caedd3be36a24def4c17a45a8bfc51a254209aacf417a36

```text
.ce/changelog/ce-386-xdist-wheelbuild.md
.ce/pr-manifests/ce-386-xdist-wheelbuild.md
validators/tests/unit/test_wheelhouse_built_surface.py
```

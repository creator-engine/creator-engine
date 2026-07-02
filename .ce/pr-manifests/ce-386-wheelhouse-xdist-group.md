# PR path manifest — ce-ops#386 · Serialize wheelhouse built-surface tests under xdist

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-386-wheelhouse-xdist-group` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=27a13f04c10a2217a259cadf7966fa314f99e6449705a691b91cb785fadee273

```text
.ce/changelog/ce-386-wheelhouse-xdist-group.md
.ce/pr-manifests/ce-386-wheelhouse-xdist-group.md
validators/tests/unit/test_packaging_contract.py
validators/tests/unit/test_wheelhouse_built_surface.py
```

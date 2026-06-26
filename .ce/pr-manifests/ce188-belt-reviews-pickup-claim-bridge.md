# PR path manifest - ce-ops#188 belt reviews-pickup claim bridge

- **Declared work class:** feature

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce188-belt-reviews-pickup-claim-bridge`
and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized
path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=baf3f4ce1e86efed691697d558a516abb56cf93999240221db1f03bf93a70c7d

```text
.ce/changelog/ce188-belt-reviews-pickup-claim-bridge.md
.ce/pr-manifests/ce188-belt-reviews-pickup-claim-bridge.md
validators/creator_engine_validator/pickup.py
validators/tests/unit/test_pickup.py
```

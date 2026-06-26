# PR path manifest — ce-ops#222 · Fail closed on unproven gVisor egress

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce222-egress-fail-closed` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=d1fd517c3fe1739cde2a8e4afb9fdc7f8af348469abd0075dd1c68f009e6714a

```text
.ce/changelog/ce222-egress-fail-closed.md
.ce/pr-manifests/ce222-egress-fail-closed.md
validators/tests/unit/test_contained_launch_proof.py
validators/tests/unit/test_gvisor_proxy_backend.py
```

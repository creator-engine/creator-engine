# PR path manifest — ce-ops#222 · fail-closed gVisor egress confinement

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-ops-222-egress-confinement` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=09cb18bd87d7b1305dafeb207c48b1d5d7e743690ee09b3438b95a99fdd887d8

```text
.ce/changelog/ce-ops-222-egress-confinement.md
.ce/pr-manifests/ce-ops-222-egress-confinement.md
deploy/dgx-runsc/README.md
validators/creator_engine_validator/runner/gvisor_proxy_backend.py
validators/tests/unit/test_gvisor_proxy_backend.py
```

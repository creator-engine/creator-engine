# PR path manifest — ce-ops#361 · Codify installer mirror release policy

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-361-installer-mirror-policy` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=3afdd04c6aac2a139683ed6167bc4bf20b707d88ec8b9674fa6feba3fbdbd4b1

```text
.ce/changelog/ce-361-installer-mirror-policy.md
.ce/pr-manifests/ce-361-installer-mirror-policy.md
docs/delivery/VERSIONING_AND_RELEASE_POLICY.md
```

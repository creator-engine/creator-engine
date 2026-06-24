# PR path manifest — ce-ops#225 · OpenBao bring-up bind-mount permission fix

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce225-openbao-bringup-perms` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=52131511c1beafef0f82689fa7b4cebb37a34da0ff8579ed548d134a9e540b1e

```text
.ce/changelog/ce225-openbao-bringup-perms.md
.ce/pr-manifests/ce225-openbao-bringup-perms.md
docs/devops/openbao/bringup-container-openbao.sh
```

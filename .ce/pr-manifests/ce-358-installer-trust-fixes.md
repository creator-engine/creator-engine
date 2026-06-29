# PR path manifest — ce-ops#358 · Fix installer uv trust boundary

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-358-installer-trust-fixes` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=e3263c141e7b47fcf1ba2862115b514e7ff2123449d656bb3ebae17fe6e3d48c

```text
.ce/changelog/ce-358-installer-trust-fixes.md
.ce/pr-manifests/ce-358-installer-trust-fixes.md
docs/install.sh
validators/tests/integration/test_install_bootstrap.py
```

# PR path manifest — ce-ops#191 · install dependency soft-inventory + re-source profile (N1)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce191-n1-install-dep-soft-inventory` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=e3ce3184dba11f0a3df32a3a47a23e4fc280f9635db6f8a9fd551f85c3bb3d05

```text
.ce/changelog/ce191-n1-install-dep-soft-inventory.md
.ce/pr-manifests/ce191-n1-install-dep-soft-inventory.md
docs/install.sh
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_installer.py
validators/tests/integration/test_install_bootstrap.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_installer.py
```

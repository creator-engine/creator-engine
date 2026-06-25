# PR path manifest — ce-ops#191 · install fault-injection fail-safe (N5)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce191-n5-fault-injection-failsafe` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=05942c956ba8afe6b859fcd196a7c76bea3bfa31f5fb7f389a58fbb6a5791c21

```text
.ce/changelog/ce191-n5-fault-injection-failsafe.md
.ce/pr-manifests/ce191-n5-fault-injection-failsafe.md
docs/install.sh
validators/creator_engine_validator/v3_cli.py
validators/tests/integration/test_install_bootstrap.py
validators/tests/unit/test_v3_cli.py
```

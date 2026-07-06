# PR path manifest — ce-ops#478 · Controller posture banner

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-478-posture-banner` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=12

AUTHORIZED_PATHS_SHA256=94ab2a79db6a2954b0f750d9e9be7aeb78a23be709c8adb9834c1337d288ec97

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-478-posture-banner.md
.ce/pr-manifests/ce-478-posture-banner.md
.ce/reference/cli.generated.md
README.md
docs/operations/SEAT_LAUNCH_GOVERNANCE_RUNBOOK.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/controller_posture.py
validators/tests/unit/test_controller_posture.py
validators/tests/unit/test_v1_docs_reconciliation.py
validators/tests/unit/test_version_boundary.py
```

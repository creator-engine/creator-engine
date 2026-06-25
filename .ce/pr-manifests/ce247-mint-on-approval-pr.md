# PR path manifest — ce-ops#247 · mint-on-approval: auto-mint approval-capability marker on trusted approval

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce247-mint-on-approval-pr` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=11

AUTHORIZED_PATHS_SHA256=6753365d7f4139e3c043aa002c419e9f92cced27dadd933bf73c1b335e73c4e6

```text
.ce/changelog/ce247-mint-on-approval-pr.md
.ce/pr-manifests/ce247-mint-on-approval-pr.md
docs/devops/openbao-approval-wall-arming.md
docs/security/ce234-approval-capability-wall.md
validators/creator_engine_validator/forge/approval_capability.py
validators/creator_engine_validator/forge/integrator_belt.py
validators/creator_engine_validator/secret_identity.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_integrator_belt.py
validators/tests/unit/test_secret_identity.py
validators/tests/unit/test_v3_cli.py
```

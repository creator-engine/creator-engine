# PR path manifest — L2-autonomy · L2 seats autonomy canary automerge arming wiring

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-l2-autonomy-arming` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=14

AUTHORIZED_PATHS_SHA256=2d398295e3ca56bd543a0e160eca4f9791fefd4c1ffce2fc570cf35001c2c5dc

```text
.ce/changelog/ce-l2-autonomy-arming.md
.ce/pr-manifests/ce-l2-autonomy-arming.md
.ce/reference/cli.generated.md
.ce/reference/schemas.generated.md
.github/workflows/automerge-actuate.yml
.github/workflows/automerge-decide.yml
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/forge/automerge_actuate_cli.py
validators/creator_engine_validator/forge/automerge_actuator.py
validators/creator_engine_validator/forge/automerge_policy.py
validators/creator_engine_validator/schemas/automerge-decision.schema.yaml
validators/creator_engine_validator/schemas/automerge-policy.schema.yaml
validators/tests/unit/test_automerge_actuator.py
validators/tests/unit/test_automerge_policy.py
```

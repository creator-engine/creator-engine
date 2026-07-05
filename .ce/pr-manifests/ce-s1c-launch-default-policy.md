# PR path manifest — ce-s1c-launch-default-policy · Default controller launch runtime policy

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-s1c-launch-default-policy` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** feature

AUTHORIZED_PATHS_COUNT=11

AUTHORIZED_PATHS_SHA256=e8599e78d391a93f1e98f8ca1e05ee1fc6c2323740059c90e42c39161da84bbd

```text
.ce/changelog/ce-s1c-launch-default-policy.md
.ce/pr-manifests/ce-s1c-launch-default-policy.md
.ce/reference/cli.generated.md
docs/contracts/runtime-policy.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/launch_runtime.py
validators/creator_engine_validator/onboard_apply.py
validators/tests/unit/test_ce_launch_cli.py
validators/tests/unit/test_contained_launch_proof.py
validators/tests/unit/test_launch_runtime.py
validators/tests/unit/test_onboard_apply.py
```

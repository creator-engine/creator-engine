# PR path manifest — creator-engine/ce-ops#410 · slice 8b validation sandbox runner

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-410-s8b-sandbox-runner` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** M

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=0914bfcd40a6dfdc905f8fd98643c3033cdaf99c2335b25f680e93703ff875a8

```text
.ce/changelog/ce-410-s8b-sandbox-runner.md
.ce/pr-manifests/ce-410-s8b-sandbox-runner.md
governance/policies/worker-container/podman-verification-v1.yaml
validators/creator_engine_validator/validation_sandbox_receipt.py
validators/creator_engine_validator/validation_sandbox_runner.py
validators/tests/unit/test_validation_sandbox_runner.py
```

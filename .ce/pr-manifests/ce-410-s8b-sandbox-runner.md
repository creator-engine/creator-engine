# PR path manifest — creator-engine/ce-ops#410 · slice 8b validation sandbox runner

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-410-s8b-sandbox-runner` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** M

AUTHORIZED_PATHS_COUNT=12

AUTHORIZED_PATHS_SHA256=703c40bbe9938e28f2bd2181c06dd9c7a27abf7ada8467fc6daec8104b327075

```text
.ce/changelog/ce-410-s8b-sandbox-runner.md
.ce/pr-manifests/ce-410-s8b-sandbox-runner.md
.ce/reference/cli.generated.md
.ce/reference/schemas.generated.md
.ce/reference/validation-sandbox-receipts.md
governance/policies/worker-container/podman-verification-v1.yaml
validators/creator_engine_validator/checks/side_effect_ledger.py
validators/creator_engine_validator/schemas/side-effect-ledger.schema.yaml
validators/creator_engine_validator/validation_sandbox_receipt.py
validators/creator_engine_validator/validation_sandbox_runner.py
validators/tests/unit/test_validation_sandbox_receipt.py
validators/tests/unit/test_validation_sandbox_runner.py
```

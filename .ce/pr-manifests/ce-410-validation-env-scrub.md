# PR path manifest — ce-ops#410 · Add validation sandbox env-scrub subprocess seam

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-410-validation-env-scrub` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=5ec6658ec0889e01fbe8c2e92eeeb8e0ed72f020b63df25f378bb1f6baa4407a

```text
.ce/changelog/ce-410-validation-env-scrub.md
.ce/pr-manifests/ce-410-validation-env-scrub.md
validators/creator_engine_validator/conveyor.py
validators/creator_engine_validator/forge/authority_contexts.py
validators/creator_engine_validator/validation_sandbox.py
validators/tests/unit/test_conveyor.py
validators/tests/unit/test_validation_sandbox.py
```

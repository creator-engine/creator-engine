# PR path manifest — ce-ops#410 · Typed authority contexts for integrator credentials

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-410-authority-contexts-core` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=d43864ed4f016c4340097ee461baebe26eeb4e994837b94ff54ed38f9177d3d0

```text
.ce/changelog/ce-410-authority-contexts-core.md
.ce/pr-manifests/ce-410-authority-contexts-core.md
validators/creator_engine_validator/forge/authority_contexts.py
validators/creator_engine_validator/forge/integrator_belt.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_authority_contexts.py
validators/tests/unit/test_integrator_belt.py
```

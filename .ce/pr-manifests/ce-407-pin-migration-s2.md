# PR path manifest — ce-ops#407 · Migrate integrator belt brain pins to probes

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-407-pin-migration-s2` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** XS

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=ceea5e1a9530fdaaa8971a7a191ec0fca4564780776f8d19b0f4073033376033

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-407-pin-migration-s2.md
.ce/pr-manifests/ce-407-pin-migration-s2.md
validators/creator_engine_validator/brain_probe.py
validators/tests/unit/test_ce_brain_drift.py
```

# PR path manifest — ce-ops#456 · Carrier generator self-cleans stale build artifacts

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-456-carrier-gen-artifact-self-clean` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=435e4a3250c32350fd6efd61352c227aac1c65e064c1b24f629c9842145706e5

```text
.ce/changelog/ce-456-carrier-gen-artifact-self-clean.md
.ce/pr-manifests/ce-456-carrier-gen-artifact-self-clean.md
validators/creator_engine_validator/carrier_gen.py
validators/tests/unit/test_carrier_gen.py
```

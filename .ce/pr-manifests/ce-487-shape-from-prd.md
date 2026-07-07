# PR path manifest — ce-ops#487 · PRD-aware shaping via ce shape --from

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-487-shape-from-prd` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=f8db0ba8004b2a9ab1e67415b45dbb7e96e7ca4d248190efe62e41131545b86c

```text
.ce/changelog/ce-487-shape-from-prd.md
.ce/pr-manifests/ce-487-shape-from-prd.md
docs/architecture/shaping-ux.md
docs/guide/complete-walkthrough.md
docs/guide/solo-dev-onboarding.md
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_shaping.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_shaping.py
```

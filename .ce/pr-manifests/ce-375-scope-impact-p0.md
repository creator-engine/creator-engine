# PR path manifest — ce-ops#375 · Warning-only Scope impact propagation

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-375-scope-impact-p0` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=165399e53e14a5aea5b4547438dd425fb85dbb5b447084b4f393dba5a63eedd9

```text
.ce/changelog/ce-375-scope-impact-p0.md
.ce/pr-manifests/ce-375-scope-impact-p0.md
.ce/reference/schemas.generated.md
docs/contracts/scope.md
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/ce_scope_impact.py
validators/creator_engine_validator/schemas/scope.schema.yaml
validators/tests/unit/test_ce_scope_impact.py
```

# PR path manifest - ce-m6 claims double-assignment block

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-m6-claims-double-assignment-block` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=8110470611a2f8a261d97a347fff5acb3f556fe9d8954f0a4f7f7e53905bd259

```text
.ce/changelog/ce-m6-claims-double-assignment-block.md
.ce/pr-manifests/ce-m6-claims-double-assignment-block.md
validators/creator_engine_validator/work_claims.py
validators/tests/unit/test_work_claims.py
```

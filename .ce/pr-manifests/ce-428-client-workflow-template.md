# PR path manifest — ce-ops#428 · client workflow template for adopted repos

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-428-client-workflow-template` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=15602adf8d08dd43580f1ca543d5418a89bcd8252fa9e3b66f7ea83773536382

```text
.ce/changelog/ce-428-client-workflow-template.md
.ce/pr-manifests/ce-428-client-workflow-template.md
validators/creator_engine_validator/onboard_apply.py
validators/tests/unit/test_onboard_apply.py
validators/tests/unit/test_onboard_apply_live.py
```

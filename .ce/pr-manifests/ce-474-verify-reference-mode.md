# PR path manifest — ce-ops#474 · Honor declared reference protections during preserved-check verify

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-474-verify-reference-mode` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=167e3959881c6c0c43a29a6dc9d84fd02294daa614bd73783a0e98029558c7a5

```text
.ce/changelog/ce-474-verify-reference-mode.md
.ce/pr-manifests/ce-474-verify-reference-mode.md
docs/contracts/brownfield-adoption.md
docs/contracts/installer.md
validators/creator_engine_validator/onboard_apply.py
validators/creator_engine_validator/onboard_apply_live.py
validators/tests/unit/test_onboard_apply.py
validators/tests/unit/test_onboard_apply_live.py
```

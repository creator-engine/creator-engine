# PR path manifest — ce-ops#474 · Honor declared reference protections during preserved-check verify

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-474-verify-reference-mode` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=ac2c5e85e178d36f8a388a43283c5a5c115e21479bcd5283676a6da01fb6e659

```text
.ce/changelog/ce-474-verify-reference-mode.md
.ce/pr-manifests/ce-474-verify-reference-mode.md
docs/contracts/brownfield-adoption.md
docs/contracts/installer.md
validators/creator_engine_validator/forge/protection_diagnostics.py
validators/creator_engine_validator/onboard_apply.py
validators/creator_engine_validator/onboard_apply_live.py
validators/tests/unit/test_onboard_apply.py
validators/tests/unit/test_onboard_apply_live.py
```

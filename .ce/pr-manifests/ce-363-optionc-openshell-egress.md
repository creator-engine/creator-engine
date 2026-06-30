# PR path manifest — ce-ops#363 · Option C OpenShell egress delegation

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-363-optionc-openshell-egress` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=b0add61dea01f5204d854205bd51b560485e3e341f6e616b126b83456e8d6a18

```text
.ce/changelog/ce-363-optionc-openshell-egress.md
.ce/pr-manifests/ce-363-optionc-openshell-egress.md
validators/creator_engine_validator/runner/os_native_backend.py
validators/tests/unit/test_orchestrator.py
validators/tests/unit/test_os_native_backend.py
```

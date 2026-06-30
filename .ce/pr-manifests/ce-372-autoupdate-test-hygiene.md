# PR path manifest — ce-ops#372 · Auto-update startup notice test hygiene

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-372-autoupdate-test-hygiene` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=d642a1098129b3d920495e0efc322d8c026d07bee12bed17f96e67992df38347

```text
.ce/changelog/ce-372-autoupdate-test-hygiene.md
.ce/pr-manifests/ce-372-autoupdate-test-hygiene.md
validators/tests/unit/test_ce_update.py
```

# PR path manifest — ce-ops#320 · Newcomer-clean narration for agent-native install verification

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-320-install-narration` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** XS

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=dbd02cc7e765aaf086448a9100ea92fb4b4745ec8374361568d83160cf59a575

```text
.ce/changelog/ce-320-install-narration.md
.ce/pr-manifests/ce-320-install-narration.md
docs/index.html
docs/llms-install.md
```

# PR path manifest - SSHSIG signing deputy design

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce-481-signing-deputy-design` and
requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=1261d90f640b1b26cbd8f5f6f082d4f696eaece380e652ead13c14b10a81847d

```text
.ce/changelog/ce-481-signing-deputy-design.md
.ce/pr-manifests/ce-481-signing-deputy-design.md
docs/design/sshsig-signing-deputy.md
```

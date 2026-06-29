# PR path manifest — ce-ops#353 · OQ-1 os-native sandbox mechanism decision package

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-oq1-os-native-mechanism` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=549524c1ca8d34b6a7cb8ae3db324cae7be0d2fa485c7f37ad79893984a209d9

```text
.ce/changelog/ce-oq1-os-native-mechanism.md
.ce/pr-manifests/ce-oq1-os-native-mechanism.md
docs/design/oq1-os-native-sandbox-mechanism.md
```

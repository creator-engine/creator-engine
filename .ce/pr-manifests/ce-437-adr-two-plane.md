# PR path manifest — ce-ops#437 · Add ADR-0014 for the two-plane OS architecture

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-437-adr-two-plane` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=801b4d319cf16c145ad280eea5812be955081fd37e83b345917f347d6b9e1330

```text
.ce/changelog/ce-437-adr-two-plane.md
.ce/pr-manifests/ce-437-adr-two-plane.md
docs/decisions/ADR-0014-two-plane-os-architecture.md
docs/design/oq1-os-native-sandbox-mechanism.md
```

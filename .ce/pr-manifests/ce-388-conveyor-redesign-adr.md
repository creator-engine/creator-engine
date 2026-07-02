# PR path manifest — ce-ops#388 · conveyor daemon security-redesign ADR

- **Declared work class:** S

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-388-conveyor-redesign-adr` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=adce8d92de73d45dc44d401294ce975a75e86d4e6271e5ee6095edefcad03a7a

```text
.ce/changelog/ce-388-conveyor-redesign-adr.md
.ce/pr-manifests/ce-388-conveyor-redesign-adr.md
docs/adr/ADR-0003-conveyor-daemon-arm-safety.md
```

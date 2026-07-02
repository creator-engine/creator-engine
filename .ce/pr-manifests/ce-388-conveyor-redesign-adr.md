# PR path manifest — ce-ops#388 · conveyor daemon security-redesign ADR

- **Declared work class:** S

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-388-conveyor-redesign-adr` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=34c753f8d5f2a1aa50f714ddb285809bf6558d2306dec90d30acf8332a359a7c

```text
.ce/changelog/ce-388-conveyor-redesign-adr.md
.ce/pr-manifests/ce-388-conveyor-redesign-adr.md
docs/adr/ADR-0004-conveyor-daemon-arm-safety.md
```

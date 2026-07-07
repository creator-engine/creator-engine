# PR path manifest - host-ops broker v1 design

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce-482-host-ops-broker-design` and
requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=b172e1ed2fe87525c6beb3bfaef4cf95bba64fc811b8459e1f9e50789afcb563

```text
.ce/changelog/ce-482-host-ops-broker-design.md
.ce/pr-manifests/ce-482-host-ops-broker-design.md
docs/design/host-ops-broker-v1.md
```

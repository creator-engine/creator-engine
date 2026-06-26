---
slug: ce-286-host-uds-persist
date: 2026-06-26
kind: pr-manifest
scope: deploy/vps-runsc
issue: ce-ops#286
---

# PR path manifest - ce-ops#286 - host UDS persistence

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce-286-host-uds-persist` and requires
this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this
carrier lists itself.

- **Declared work class:** tiny

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=48a2c653aadea29061682dcf58b174a6890ffb6eb1f15b12f5fe2c5390211235

```text
.ce/changelog/ce-286-host-uds-persist.md
.ce/pr-manifests/ce-286-host-uds-persist.md
deploy/vps-runsc/README.md
```

# PR path manifest - ce-openbao-vps-standup

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
This carrier lists the closed authorized path-set for the OpenBao approval-wall
arming runbook update.

- **Declared work class:** tiny

Scope:
Value-free docs-only handoff for the controller/operator to finish OpenBao
approval-wall TEST proof and later production arming decisions without storing
secret values in the repository.

Per-file purpose:
- **`.ce/changelog/ce-openbao-vps-standup.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-openbao-vps-standup.md`** *(A)* - this closed path-set
  carrier.
- **`docs/devops/openbao-approval-wall-arming.md`** *(A)* - day-2 runbook.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=7ad549acec68316bab05d30977d8a5dc8f43afae21f5de95fd392c3d6f319a5e

```text
.ce/changelog/ce-openbao-vps-standup.md
.ce/pr-manifests/ce-openbao-vps-standup.md
docs/devops/openbao-approval-wall-arming.md
```

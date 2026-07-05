# PR path manifest — ce-ops#443 · Add conveyor daemon stuck-lease recovery runbook

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-443-stuck-lease-runbook` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=2ea51556145130bd3b1af3ed1e65fa7b6987e6caf5c60b09e787a4653dde1bce

```text
.ce/changelog/ce-443-stuck-lease-runbook.md
.ce/pr-manifests/ce-443-stuck-lease-runbook.md
deploy/conveyor-daemon/RUNBOOK.md
playbooks/controller/runbooks/conveyor-daemon-stuck-lease.md
```

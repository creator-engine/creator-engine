# PR path manifest — ce-ops#443 · Add conveyor daemon stuck-lease recovery runbook

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-443-stuck-lease-runbook` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=cd2c0cf0c082d97699014417cf03b461ff307b44ade7cd88147bfd7fa5185dc3

```text
.ce/changelog/ce-443-stuck-lease-runbook.md
.ce/pr-manifests/ce-443-stuck-lease-runbook.md
playbooks/controller/runbooks/conveyor-daemon-stuck-lease.md
```

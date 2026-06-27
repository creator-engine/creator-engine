# PR path manifest — ce-ops#319 · pilot co-drive runbook (internal)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-arad-pilot-runbook` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=c5d3b27b0e267c2b445f67b5830a87a53e50d0da6afc3dd4d7f4b190f69a89da

```text
.ce/changelog/ce-arad-pilot-runbook.md
.ce/pr-manifests/ce-arad-pilot-runbook.md
playbooks/controller/runbooks/arad-pilot.md
```

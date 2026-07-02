# PR path manifest — ce-ops#398 · Controller standup duty manifest and runbook

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-398-controller-standup-docs` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=8d447d11329abf8c4a983653481c5b34b18fbc1353c2181c0e2cd461b34d09f0

```text
.ce/changelog/ce-398-controller-standup-docs.md
.ce/pr-manifests/ce-398-controller-standup-docs.md
playbooks/controller/duties.yaml
playbooks/controller/runbooks/controller-standup.md
```

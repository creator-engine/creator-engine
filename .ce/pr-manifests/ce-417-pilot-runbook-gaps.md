# PR path manifest — creator-engine/ce-ops#417 · Document pilot brownfield apply prerequisites

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-417-pilot-runbook-gaps` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=02c87c85548955fc0053cd0f8a4f068d15ec4a02bf8ee86f8c3202af77e50aac

```text
.ce/changelog/ce-417-pilot-runbook-gaps.md
.ce/pr-manifests/ce-417-pilot-runbook-gaps.md
docs/contracts/installer.md
docs/guide/pilot-runbook.md
```

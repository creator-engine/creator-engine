# PR path manifest — creator-engine/ce-ops#452 · Canary QA worker role

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-452-canary-qa-worker-role` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=20814eba1dd0a6ddb62622f1bc45e3fb56fe840f3266ee2cd5621860946aee00

```text
.ce/changelog/ce-452-canary-qa-worker-role.md
.ce/pr-manifests/ce-452-canary-qa-worker-role.md
.claude/agents/README.md
.claude/agents/canary_qa.md
```

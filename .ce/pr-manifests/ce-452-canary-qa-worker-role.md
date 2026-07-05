# PR path manifest — creator-engine/ce-ops#452 · Canary QA worker role

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-452-canary-qa-worker-role` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=5f6eecbda17c027a85780e42c9da19b7426ff3f218e76643e4423c05ad004cc2

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-452-canary-qa-worker-role.md
.ce/pr-manifests/ce-452-canary-qa-worker-role.md
.claude/agents/README.md
.claude/agents/canary_qa.md
validators/tests/unit/test_ce_brain_drift.py
```

# PR path manifest — ce-ops#413 · Auto-merge Tier B brain supersede chores

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-413-automerge-tier-b` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=fa99a7f5e7403103fa3d3061915788db67a35551975e12caff6500ce206b6372

```text
.ce/changelog/ce-413-automerge-tier-b.md
.ce/pr-manifests/ce-413-automerge-tier-b.md
.github/workflows/automerge-actuate.yml
.github/workflows/automerge-decide.yml
validators/creator_engine_validator/forge/automerge_actuator.py
validators/creator_engine_validator/forge/automerge_policy.py
validators/tests/unit/test_automerge_actuator.py
validators/tests/unit/test_automerge_policy.py
```

# PR path manifest — ce-ops#412 · Auto-merge Tier A carrier/changelog split-tier

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-412-automerge-tier-a` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** XS

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=9794db359842cd72f6c6550876ca17eb94a121105a2a35f2699191b8566b7fcb

```text
.ce/changelog/ce-412-automerge-tier-a.md
.ce/pr-manifests/ce-412-automerge-tier-a.md
.github/workflows/automerge-actuate.yml
.github/workflows/automerge-decide.yml
validators/creator_engine_validator/forge/automerge_actuator.py
validators/creator_engine_validator/forge/automerge_policy.py
validators/tests/unit/test_automerge_actuator.py
validators/tests/unit/test_automerge_policy.py
```

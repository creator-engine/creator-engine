# PR path manifest — ce-a3-docs-envelope-tiers · Extend automerge docs envelope tier

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-a3-docs-envelope-automerge` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** M

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=c283d24254d27fd21783dad95f936c47b9bb936c9d18d829cb7e605a8291e781

```text
.ce/changelog/ce-a3-docs-envelope-automerge.md
.ce/pr-manifests/ce-a3-docs-envelope-automerge.md
validators/creator_engine_validator/forge/automerge_actuator.py
validators/creator_engine_validator/forge/automerge_policy.py
validators/tests/unit/test_automerge_actuator.py
validators/tests/unit/test_automerge_policy.py
```

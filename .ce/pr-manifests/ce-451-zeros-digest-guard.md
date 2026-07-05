# PR path manifest — creator-engine/ce-ops#451 · Reject placeholder surface sha256 digests

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-451-zeros-digest-guard` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** tiny

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=559fb6c9438e355551a428721ab6bcdb66c66cd0943f3703fc331100ab9642d1

```text
.ce/changelog/ce-451-zeros-digest-guard.md
.ce/pr-manifests/ce-451-zeros-digest-guard.md
validators/creator_engine_validator/checks/surfaces_manifest.py
validators/tests/unit/test_surfaces_manifest.py
```

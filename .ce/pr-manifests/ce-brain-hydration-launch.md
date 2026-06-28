# PR path manifest - ce-ops#79 - BRAIN-A Hydration Launch

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-brain-hydration-launch` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=9a2e2f4d540b1644f2b91a759360d970f77bffd86b8bc8fc447ccda9260b5a8c

```text
.ce/changelog/ce-brain-hydration-launch.md
.ce/pr-manifests/ce-brain-hydration-launch.md
validators/creator_engine_validator/launch_runtime.py
validators/tests/unit/test_launch_runtime.py
```

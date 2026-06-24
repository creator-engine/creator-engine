# PR path manifest — ce-ops#219 · GitHub API-surface classifier for Ring-1 hook

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-hook-apisurface-classifier` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=85dd52ee4a6f5360946af181687808665643a22749346ed24b9f0747b19065fe

```text
.ce/changelog/ce-hook-apisurface-classifier.md
.ce/pr-manifests/ce-hook-apisurface-classifier.md
validators/creator_engine_validator/hook_check.py
validators/tests/unit/test_hook_check.py
```

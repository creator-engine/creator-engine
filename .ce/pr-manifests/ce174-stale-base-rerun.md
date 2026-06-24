# PR path manifest — 174 · path-manifest gate resolves live PR base/head, fails closed on stale re-run

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce174-stale-base-rerun` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=bfb8807c3e7c3781d30e024cf6065d75e7652145dc612c2624e1cc4598163133

```text
.ce/changelog/ce174-stale-base-rerun.md
.ce/pr-manifests/ce174-stale-base-rerun.md
.github/workflows/validate.yml
validators/tests/unit/test_work_sizing_floor_ci_wiring.py
```

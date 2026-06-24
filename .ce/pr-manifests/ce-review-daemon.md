# PR path manifest — ce-ops#411 · review-pickup daemon — autonomous review fan-out

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-review-daemon` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=f4a92b15864cf6bb0939d9fc8067c3db1069d5aed8f0604b3aba98f40960a105

```text
.ce/changelog/ce-review-daemon.md
.ce/pr-manifests/ce-review-daemon.md
docs/operations/REVIEW_PICKUP_DAEMON.md
validators/creator_engine_validator/forge/review_pickup.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_review_pickup.py
```

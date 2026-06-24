# PR path manifest — 227 · Wave-B — herdr send-keys Enter commit + sha256 verify-after-render delivery

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce227-wave-b` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=64ccfabe2bd3463bb76b83860c077ee42a47e8e1341a8e24e4173b298c697fa0

```text
.ce/changelog/ce227-wave-b.md
.ce/pr-manifests/ce227-wave-b.md
validators/creator_engine_validator/runner/herdr_session.py
validators/tests/unit/test_herdr_session.py
```

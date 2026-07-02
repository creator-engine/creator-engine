# PR path manifest - ce-370-prbody-local-parity - local validate-pr PR body parity

- **Declared work class:** XS

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-370-prbody-local-parity` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=a5a4da9b0edbfdbb1748f7818000879d62aeed885db9a0ca475aacb674fd0d89

```text
.ce/changelog/ce-370-prbody-local-parity.md
.ce/pr-manifests/ce-370-prbody-local-parity.md
validators/creator_engine_validator/checks/git_helpers.py
validators/creator_engine_validator/checks/test_coupling.py
validators/creator_engine_validator/checks/work_sizing_floor.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_pr_preflight.py
validators/tests/unit/test_test_coupling.py
```

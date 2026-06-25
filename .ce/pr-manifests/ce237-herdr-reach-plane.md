# PR path manifest — ce-ops#237 · herdr authenticated reach-plane prototype + design

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce237-herdr-reach-plane` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=abe28bb7b54dfedd0904bb0fc2b9982872ed8e4c5cf7e6c644f4ccab765fb9b3

```text
.ce/changelog/ce237-herdr-reach-plane.md
.ce/pr-manifests/ce237-herdr-reach-plane.md
docs/operations/HERDR_OPERATOR_REACH_PLANE.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/runner/herdr_session.py
validators/tests/unit/test_ce_herdr_cli.py
validators/tests/unit/test_herdr_session.py
validators/tests/unit/test_v1_docs_reconciliation.py
```

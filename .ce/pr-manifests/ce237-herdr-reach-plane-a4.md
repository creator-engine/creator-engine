# PR path manifest - ce237-herdr-reach-plane-a4

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for ce-ops#237 A4. CI runs `verify-path-manifest --base
<sha> --manifest-dir .ce/pr-manifests --head-ref
ce237-herdr-reach-plane-a4` and requires this PR's `base..HEAD` diff to equal
exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=56aa69102647adaa6975080824cebd963ed6c6356c3ffe036399a329db2143cc

```text
.ce/changelog/ce237-herdr-reach-plane-a4.md
.ce/pr-manifests/ce237-herdr-reach-plane-a4.md
docs/operations/HERDR_OPERATOR_REACH_PLANE.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/runner/herdr_session.py
validators/tests/unit/test_ce_herdr_cli.py
validators/tests/unit/test_herdr_session.py
```

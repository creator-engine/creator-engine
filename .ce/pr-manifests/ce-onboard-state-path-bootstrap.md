# PR path manifest — ce-ops#197 · Actionable RED-G-4 onboard guidance

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-onboard-state-path-bootstrap` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=a5454db112d00c8379f0d56643aaf52011d1f6a6c9afc0d41532d8118082759c

```text
.ce/changelog/ce-onboard-state-path-bootstrap.md
.ce/pr-manifests/ce-onboard-state-path-bootstrap.md
validators/creator_engine_validator/ce_onboard.py
validators/tests/unit/test_ce_onboard.py
validators/tests/unit/test_ce_onboard_cli.py
```

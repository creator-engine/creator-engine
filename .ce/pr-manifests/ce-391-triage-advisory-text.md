# PR path manifest — ce-ops#391 · Surface commissioned unscheduled pickup triage advisory text

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-391-triage-advisory-text` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** XS

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=c5aff5935c124dc9e0d0d52a63300204bf4fe59616192999462b4ecfa62353f2

```text
.ce/changelog/ce-391-triage-advisory-text.md
.ce/pr-manifests/ce-391-triage-advisory-text.md
validators/creator_engine_validator/ce_cli.py
validators/tests/unit/test_forge_triage.py
```

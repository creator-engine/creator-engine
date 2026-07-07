# PR path manifest — ce-ops#495 · Codify forge housekeeping runbook

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-495-forge-housekeeping-runbook` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=08c8f88a68d7eca00148d59384317ef5926b2eb193670cb928482b1a729fe1f0

```text
.ce/changelog/ce-495-forge-housekeeping-runbook.md
.ce/pr-manifests/ce-495-forge-housekeeping-runbook.md
docs/operations/FORGE_HOUSEKEEPING_RUNBOOK.md
validators/creator_engine_validator/public_docs_confidentiality.py
validators/creator_engine_validator/takeover_runtime.py
validators/tests/unit/test_ce_takeover_cli.py
```

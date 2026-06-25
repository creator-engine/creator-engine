# PR path manifest — ce-ops#235 · emergency stop alias

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce235-emergency-stop-alias` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=8849ef1e8bf956102e6ecc17a0dd38dffd3bdac02496389d9e937d609e506b42

```text
.ce/changelog/ce235-emergency-stop-alias.md
.ce/pr-manifests/ce235-emergency-stop-alias.md
docs/operations/INTEGRATOR_BELT_DAEMON.md
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_integrator_belt.py
```

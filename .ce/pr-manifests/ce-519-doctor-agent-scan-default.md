# PR path manifest — ce-ops#519 · doctor agent scan default

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-519-doctor-agent-scan-default` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** S

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=c2778d5ff2abfe8820082a71ca6f74ef82e2e5f9ea17da954b152bfa6093a513

```text
.ce/changelog/ce-519-doctor-agent-scan-default.md
.ce/pr-manifests/ce-519-doctor-agent-scan-default.md
validators/creator_engine_validator/doctor_runtime.py
validators/tests/unit/test_ce_doctor_cli.py
```

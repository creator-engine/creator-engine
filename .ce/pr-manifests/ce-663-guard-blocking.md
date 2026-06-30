# PR path manifest — ce-ops#364 · Make install-spec signature guard blocking

- **Declared work class:** story

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-663-guard-blocking` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=e2c3f77a0183373e480b7c56ebcc4c53676884de202b0040cfd5976e100e9e96

```text
.ce/changelog/ce-663-guard-blocking.md
.ce/pr-manifests/ce-663-guard-blocking.md
.github/workflows/validate.yml
validators/creator_engine_validator/checks/install_spec_signature_guard.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_install_spec_signature_guard.py
validators/tests/unit/test_pr_preflight.py
validators/tests/unit/test_work_sizing_floor_ci_wiring.py
```

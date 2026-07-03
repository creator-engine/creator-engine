# PR path manifest — ce-ops#407 · Migrate pr_preflight brain pins to probes

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-407-pin-migration-s1` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** XS

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=22d404afcfa9e3e4e7a3e371de5498ad92453ec6348b6254f6e69114afc8b8df

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-407-pin-migration-s1.md
.ce/pr-manifests/ce-407-pin-migration-s1.md
validators/creator_engine_validator/brain_probe.py
validators/tests/unit/test_ce_brain_drift.py
```

# PR path manifest — ce-ops#21 · auto-carrier — ce carrier generates + self-verifies changelog + path-manifest

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-auto-carrier` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=c33b0c9801eaf269d453d670d4e20bbaefc45c71aff5e9fe84e7f3676729f433

```text
.ce/changelog/ce-auto-carrier.md
.ce/pr-manifests/ce-auto-carrier.md
validators/creator_engine_validator/carrier_gen.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_carrier_gen.py
```

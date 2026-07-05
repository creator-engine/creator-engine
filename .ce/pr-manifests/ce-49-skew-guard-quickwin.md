# PR path manifest — creator-engine/ce-ops#49 · quick-win: refuse gate commands under stale-wheel version skew

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-49-skew-guard-quickwin` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=489ba79a05386f0af59789bc816937f5022cb1a1c562b3e92af6b4daf2a1d1f0

```text
.ce/changelog/ce-49-skew-guard-quickwin.md
.ce/pr-manifests/ce-49-skew-guard-quickwin.md
validators/creator_engine_validator/ce_cli.py
validators/tests/unit/test_ce_cli_skew_guard.py
```

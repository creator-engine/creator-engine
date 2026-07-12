# PR path manifest — M2 · Governed review-acting spawn provider — sequenced integration

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-m2-spawn-provider-integration` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** M

AUTHORIZED_PATHS_COUNT=12

AUTHORIZED_PATHS_SHA256=e9a274f5f3745a8b49cfc45461c48cdb84715b464b1f6e0dbf1c72b6a24274ab

```text
.ce/changelog/ce-m2-spawn-provider-integration.md
.ce/pr-manifests/ce-m2-spawn-provider-integration.md
.ce/reference/cli.generated.md
docs/reference/cli.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/forge/review_acting.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_ce_cli_v3_shim.py
validators/tests/unit/test_gate_daemons_systemd.py
validators/tests/unit/test_review_acting.py
validators/tests/unit/test_v1_docs_reconciliation.py
validators/tests/unit/test_v3_cli.py
```

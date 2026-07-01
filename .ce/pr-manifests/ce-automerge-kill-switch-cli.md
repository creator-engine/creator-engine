# PR path manifest — L2 auto-merge P1 · Automerge kill-switch CLI

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-automerge-kill-switch-cli` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** S

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=35dee25844d35e9a23e872aef296ff8631de9849002c20fc0cf6de22508e97b2

```text
.ce/changelog/ce-automerge-kill-switch-cli.md
.ce/pr-manifests/ce-automerge-kill-switch-cli.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/forge/automerge_policy.py
validators/tests/unit/test_automerge_actuator.py
validators/tests/unit/test_automerge_status.py
validators/tests/unit/test_v1_docs_reconciliation.py
```

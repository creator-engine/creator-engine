# PR path manifest — ce-ops#313 · Automerge status decision-log reader

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-automerge-status` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=0e9cb727f748ede87fbdf1cce44fd3c899112086a2000ef37147cd612cd09d01

```text
.ce/changelog/ce-automerge-status.md
.ce/pr-manifests/ce-automerge-status.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/forge/automerge_policy.py
validators/tests/unit/test_automerge_status.py
```

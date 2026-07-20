# PR path manifest — ce-ops#636 · brain correction statement preservation

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce636-brain-correct-statement-preservation` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=0a331cf3b11cb3dceb20f0a0efe8074f02f8787272407ef09155369d45b48c19

```text
.ce/changelog/ce636-brain-correct-statement-preservation.md
.ce/pr-manifests/ce636-brain-correct-statement-preservation.md
validators/creator_engine_validator/brain_runtime.py
validators/creator_engine_validator/ce_cli.py
validators/tests/integration/test_ce_brain_cli.py
```

# PR path manifest — ce-ops#354 · Support agent Phase B model-backend wiring

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-supportagent-phaseb-model-wiring` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=8e39a004dcaaffaf3afec93580e7017854160f7a970bbb8cea77d84aaeb741dd

```text
.ce/changelog/ce-supportagent-phaseb-model-wiring.md
.ce/pr-manifests/ce-supportagent-phaseb-model-wiring.md
validators/creator_engine_validator/support_runtime.py
validators/tests/unit/test_support_agent_p0.py
validators/tests/unit/test_support_agent_phase1.py
```

# PR path manifest — ce-ops#354 · Support agent Phase-1 answering path

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-354-support-agent-phase1` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** feature

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=dbb63428ad59ae25e31c31b3e47a395947ba75b0463eea5cb70c2e40f49d4370

```text
.ce/changelog/ce-354-support-agent-phase1.md
.ce/pr-manifests/ce-354-support-agent-phase1.md
validators/creator_engine_validator/support_bundle.py
validators/creator_engine_validator/support_runtime.py
validators/tests/unit/test_support_agent_p0.py
validators/tests/unit/test_support_agent_phase1.py
```

# PR path manifest — ce-supportagent-zeroleak-eval · Support agent zero-leak eval harness

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-supportagent-zeroleak-eval` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=7db50e43d9060b8f5fa5295aeda6ee8d6a9ea83c8bd7fafb094868d8d8670a99

```text
.ce/changelog/ce-supportagent-zeroleak-eval.md
.ce/pr-manifests/ce-supportagent-zeroleak-eval.md
validators/creator_engine_validator/support_eval.py
validators/tests/unit/fixtures/support_agent_zero_leak_cases.json
validators/tests/unit/test_support_agent_zero_leak_eval.py
```

# PR path manifest — ce-ops#360 · Expand support-agent zero-leak eval corpus

- **Declared work class:** story

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-supportagent-eval-corpus-expand` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=8af8ed3eac997b55563570fc7dcb7d9eb9b7ca85befbd81dd1a9246975718981

```text
.ce/changelog/ce-supportagent-eval-corpus-expand.md
.ce/pr-manifests/ce-supportagent-eval-corpus-expand.md
validators/tests/unit/fixtures/support_agent_zero_leak_cases.json
validators/tests/unit/test_support_agent_zero_leak_eval.py
```

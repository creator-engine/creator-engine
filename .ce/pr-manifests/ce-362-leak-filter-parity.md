# PR path manifest — ce-ops#362 · support-agent leak filter parity

- **Declared work class:** story

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-362-leak-filter-parity` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=78d46045d5e375e1c323144a25924b901b7765fb5c4c3ba88335d563d5c0f41f

```text
.ce/changelog/ce-362-leak-filter-parity.md
.ce/pr-manifests/ce-362-leak-filter-parity.md
validators/creator_engine_validator/support_eval.py
validators/creator_engine_validator/support_leak_rules.py
validators/creator_engine_validator/support_runtime.py
validators/tests/unit/test_support_agent_zero_leak_eval.py
```

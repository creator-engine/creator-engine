# PR path manifest — ce-ops#354 · Support agent Phase C Discord channel adapter

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-supportagent-discord-adapter` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=4804a7d1cac34090802eb012f9f6e158d0f0db013a41d2b65c84daaa720bd974

```text
.ce/changelog/ce-supportagent-discord-adapter.md
.ce/pr-manifests/ce-supportagent-discord-adapter.md
validators/creator_engine_validator/support_discord_adapter.py
validators/tests/unit/test_support_discord_adapter.py
```

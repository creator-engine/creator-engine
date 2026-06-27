# PR path manifest -- ce-ops#297 ClaudeCodeAdapter lifecycle

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce297-claude-code-adapter` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Closes creator-engine/ce-ops#297

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=8a8577665c31d18cce66104d47a21d9299f39223485f87a97b4f9a52ad5360fc

```text
.ce/changelog/ce297-claude-code-adapter.md
.ce/pr-manifests/ce297-claude-code-adapter.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/harness_adapters/claude_code_adapter.py
validators/tests/unit/test_claude_code_adapter_lifecycle.py
validators/tests/unit/test_version_boundary.py
```

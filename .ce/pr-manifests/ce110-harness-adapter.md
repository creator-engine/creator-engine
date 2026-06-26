---
slug: ce110-harness-adapter
date: 2026-06-26
kind: story
scope: validators/creator_engine_validator/harness_adapter.py, validators/creator_engine_validator/harness_adapters/
issue: ce-ops#110
---

Ring-1 harness-adapter layer: HarnessAdapter base, CapabilityDeclaration schema, CodexAdapter (external_gate-only), ClaudeCodeAdapter skeleton, focused tests.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=1010b9812ed21f795659ca0a5a4126cbed165a2c9d4163c0b2372a4a0b923717

```text
.ce/changelog/ce110-harness-adapter.md
.ce/pr-manifests/ce110-harness-adapter.md
validators/creator_engine_validator/harness_adapter.py
validators/creator_engine_validator/harness_adapters/__init__.py
validators/creator_engine_validator/harness_adapters/claude_code_adapter.py
validators/creator_engine_validator/harness_adapters/codex_adapter.py
validators/tests/test_harness_adapter.py
```

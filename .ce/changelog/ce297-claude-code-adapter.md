---
slug: ce297-claude-code-adapter
date: 2026-06-27
kind: added
scope: harness_adapters — ClaudeCodeAdapter lifecycle implementation
issue: ce-ops#297
---

Implements 7 lifecycle method stubs in `ClaudeCodeAdapter` (the #110 skeleton)
with fail-closed logic. Each method returns a context dict merged with
Claude Code-specific metadata: harness identity, enforcement status, sandbox
identity, and enforcement mechanism fields.

Adds `validators/tests/unit/test_claude_code_adapter_lifecycle.py` with unit
tests covering all 7 methods, context merging, and sentinel value assertions.

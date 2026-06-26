---
slug: ce132-cleanroom-install-s1
date: 2026-06-26
kind: fix
scope: install
issue: 132
---

**fix(ce-ops#132): clean-room install S1 blockers.**

Closes ce-ops#132 (pilot-readiness S1 blockers).

Summary:
- Add upfront Git bootstrap prerequisite refusal to clean-room install.
- Route userspace onboard apply through the selected live-capable driver seam.
- Surface tmux/codex runtime prerequisites in onboard plan output.

Tests:
- uv run --project validators --with pytest pytest validators/tests/unit/test_onboard_apply.py validators/tests/unit/test_v3_cli_cleanroom.py -q

- **Declared work class:** story

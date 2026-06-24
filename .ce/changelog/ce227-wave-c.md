### ce-ops#227 — Wave-C: canary-blocker fixes (commit-confirm, dep-minimal hook, headless hook-trust)

- **Crit 4:** `_input_line_pending` now inspects only the active input line (`_active_input_region`), not the scrollback tail — committed text in history no longer false-positives as "pending" (fixes the every-commit false alarm the canary caught).
- **Crit 5a:** `hook_check` lazy-imports `yaml` + `.checks` (helpers) instead of at module load — the Ring-1 PreToolUse deny path runs stdlib-only, so the hook no longer crashes (and fail-closed-denies-everything) when PyYAML is absent in the contained image.
- **Crit 5b:** runsc launchers pass `--dangerously-bypass-hook-trust` so codex runs managed hooks headlessly (bypasses the interactive trust prompt, not the hook itself).

---
slug: ce219-codex-pretooluse-hook
ticket: ce-ops#219
type: fixed
scope: codex hooks
---

Hardens the Codex PreToolUse adapter fail-closed path:

- Keeps malformed Codex hook input fail-closed.
- Redacts `hook-check` invocation failure details from Codex deny reasons so
  child stdout, child stderr, and runner exception text cannot become a live
  hook-output leak surface.
- Adds regression coverage for synthetic secret material in failed
  `hook-check` output and runner exceptions.

---
slug: ce593-596-socket-fixture-hardening
date: 2026-07-22
kind: fixed
scope: validator test infrastructure
issue: #593 and #596
---

**Harden unix socket fixture cleanup and annotation.**

- #593: keep AF_UNIX temporary-root validation fail-closed while running it under the existing cleanup guard, so a rejected fresh root is removed.
- #596: describe the yielding fixture as `Generator[Path, None, None]` without changing runtime behavior.

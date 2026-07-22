---
slug: ce645-fixture-followups
date: 2026-07-22
kind: test
scope: validators-tests
issue: ce-ops#645
---

**Cover AF_UNIX fixture symlink cleanup.**

- Adds a real symlink replacement regression for `unix_socket_tmp_path` cleanup, proving cleanup unlinks the link and preserves its target contents.
- Keeps the fixture implementation unchanged: this is test-infrastructure coverage, not a runtime-surface change.

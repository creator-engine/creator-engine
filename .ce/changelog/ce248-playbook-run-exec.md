---
slug: ce248-playbook-run-exec
date: 2026-06-26
kind: feature
scope: playbook-runtime
issue: ce-ops#248
---

**Runnable CE playbooks.**

- Added `ce playbook list` discovery for repo-native `workflow.ce.yml` playbooks.
- Added `ce playbook run` execution with dry-run planning, per-step PASS/FAIL output, and final status.
- Documented optional runtime step fields for dual-use playbooks and covered dry-run, mocked success, and malformed rejection.

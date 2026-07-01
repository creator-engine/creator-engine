---
slug: ce-347-autoreview-runmode-cli
date: 2026-07-01
kind: added
scope: egress self-review broker
issue: ce-ops#347
---

**AutoReview run-mode CLI wiring.**

- **Declared work class:** S
- Added focused tests for AutoReview broker `--run-mode` CLI behavior, including `strangeLoop` host selection, fail-closed absent/dev mode, payload injection refusal, and help output coverage.

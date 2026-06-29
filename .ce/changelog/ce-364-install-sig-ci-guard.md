---
slug: ce-364-install-sig-ci-guard
date: 2026-06-29
kind: added
scope: validators / CI
issue: ce-ops#364
---

**Add advisory install-spec signature guard.**

Added a fail-closed install-spec signature scanner for docs/llms-install.md and any versioned mirrors, with temporary advisory workflow and local preflight wiring until the controller re-signs the served spec.

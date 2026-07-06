---
slug: ce-477-takeover-core
date: 2026-07-06
kind: added
scope: validator CLI
issue: ce-ops#477
---

**Add ce takeover dry-run core.**

- Added the read-only ce takeover planner/evidence packet for Slice B.
- Wired dry-run text and JSON output through the existing launch runtime Ring-0 preflight.
- Added focused CLI coverage for evidence gaps, no-mutation dry-run behavior, and harness validation refusals.

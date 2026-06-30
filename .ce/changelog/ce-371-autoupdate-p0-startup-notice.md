---
slug: ce-371-autoupdate-p0-startup-notice
date: 2026-06-30
kind: added
scope: signed updater / CLI startup
issue: ce-ops#371
---

**Auto-update P0 startup notice.**

- **Declared work class:** story
- Added a signed, spec-only startup update check that verifies llms-install.md and trust anchors without fetching wheel artifacts.
- Added an interactive-only startup notice with cache-window suppression, fail-open timeout/error handling, posture gating for governed/contained/fleet seats, and CE_UPDATE_CHECK=off opt-out.

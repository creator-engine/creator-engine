---
slug: ce583-vps-manifest-digest-coupling
date: 2026-07-25
kind: fixed
scope: VPS runsc manifest-image test coupling
issue: ce-ops#583
---

**Derive VPS launcher test expectations from their manifest-owned contract.**

- Replace the stale test-only default image digest with an independent read of
  the canonical VPS runsc manifest entry.
- Prove the launcher follows a valid alternative manifest rather than a
  fixed default image value.

Finding 1 and findings 8–9 remain open and are deliberately untouched.

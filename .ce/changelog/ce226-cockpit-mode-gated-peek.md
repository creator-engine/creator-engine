---
slug: ce226-cockpit-mode-gated-peek
date: 2026-06-25
kind: feature
scope: cockpit
issue: ce-ops#226
---

**mode-gated cockpit peek.**

- **Declared work class:** feature
- Adds the cockpit peek JSON/readmodel surface with Dev opt-out and CEO/strangeLoop opt-in defaults.
- Adds a render-only cockpit Peek tab plus injected handler request seam for herdr attach/send-input triggers.
- Surfaces headless targets as blocked for interactive peek instead of treating log output as intervention-capable.

---
slug: ce226-cockpit-peek
date: 2026-06-26
kind: feature
scope: cockpit
issue: ce-ops#226
---

**headless cockpit peek surface.**

- **Declared work class:** feature
- Adds headless visual-inspect peek triggers for live controller log surfaces without reading or tailing logs in the readmodel.
- Routes mode-gated headless input requests only when the terminal surface advertises an input/control endpoint.
- Keeps herdr attach/send triggers on the existing cockpit seam and does not modify herdr attach or transport code.

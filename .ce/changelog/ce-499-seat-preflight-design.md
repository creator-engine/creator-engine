---
slug: ce-499-seat-preflight-design
date: 2026-07-07
kind: added
scope: seat preflight design
issue: ce-ops#499
---

**Seat-side preflight design.**

- Added a design for a seat-side pre-READY preflight that blocks stale generated references and malformed carriers before controller harvest.
- Recommended a `ce validate-pr` seat-ready profile over a new top-level verb to preserve CI parity.
- Captured fail-closed semantics, host resource bounds, dispatch checklist integration, and public-docs confidentiality expectations.
- **Declared work class:** S

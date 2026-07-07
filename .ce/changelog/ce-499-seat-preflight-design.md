---
slug: ce-499-seat-preflight-design
date: 2026-07-07
kind: added
scope: seat preflight design
issue: ce-ops#499
---

**Seat-side preflight design.**

- Added a design for a seat-side pre-READY preflight that blocks stale generated references and malformed carriers before controller harvest.
- Recommended a new `ce validate-pr --profile seat-ready` successor profile over a new top-level verb to preserve CI parity while leaving legacy `contained-seat` harvest-side-carrier behavior intact.
- Captured fail-closed semantics, host resource bounds, dispatch checklist integration, and public-docs confidentiality expectations.
- Clarified autogen check reuse, `ENV-SKIP`/`BLOCKED` implementation ownership, `-n 4` enforcement, and zero controller-side repair measurement.
- **Declared work class:** S

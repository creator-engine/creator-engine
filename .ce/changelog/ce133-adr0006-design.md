---
slug: ce133-adr0006-design
date: 2026-06-19
kind: added
scope: architecture
issue: ce-ops#133
---

Added proposed ADR-0006, a design-only decision record for moving derived
first-party app wheels out of ordinary source PRs and into CI-built, signed
release artifacts.

The ADR covers reproducible vendored dependencies, merge-queue wheel/source
verification, ce-ops#91 doc-currency touchpoints, ce-ops#65 changelog-gate
touchpoints, and the phased gates needed to end the recurring per-PR app-wheel
rebuild tax.

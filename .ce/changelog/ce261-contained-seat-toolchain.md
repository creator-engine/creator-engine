---
slug: ce261-contained-seat-toolchain
date: 2026-06-26
kind: added
scope: contained seat image
issue: ce-ops#261
---

Bakes the pinned pytest-xdist validator test toolchain into the contained seat images.

- Adds pytest, pytest-xdist, and pytest-timeout to the DGX runsc Dockerfile
  with pinned versions matching the host validator environment.
- Mirrors the same toolchain into the VPS runsc Dockerfile for parity.
- Ensures contained workers can run the full validator suite natively
  without host-side injection.

---
slug: ce115-wave1-controller-containment
date: 2026-06-19
kind: changed
scope: controller containment gates 1-2
issue: ce-ops#115
---

Implemented Wave 1 Gates 1 and 2 for Controller containment. The Controller
Runtime Contract now declares `role: controller`, accepts the contained
Controller posture, and validates the contained state root, forbidden-surface
floor, and non-private-key request/handle names.

Added the DGX Controller runsc/gVisor sibling artifact for the merged
`deploy/dgx-runsc/` precedent: a minimal seat-matched image, a dry-runable
Claude Controller wrapper, and image-build/runtime docs. Gates 3-7 remain
excluded.

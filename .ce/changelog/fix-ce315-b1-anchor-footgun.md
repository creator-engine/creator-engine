---
slug: ce324-release-anchor-footgun
date: 2026-06-27
kind: fixed
scope: release staging / signing-anchor parameterization
issue: ce-ops#324
---

**Phase A release staging: invert the signing-anchor default to the public trust root.**

- The release-stage default signing anchor is now `ce-root-v1`, the public trust
  root the install recipe in `docs/llms-install.md` is authored for. Staging a
  public release requires NO recipe rewrite and emits a consistent
  `key_id: ce-root-v1`, `-I ce-root-v1` verify recipe, and SIGNING-INSTRUCTIONS.
- The recipe rewrite now fires only for the dev/test anchor (`ce-dev1-root-v1`),
  rewriting the source `ce-root-v1` principal exactly once (fail-closed preserved).
- Added a fail-closed guard: the staged `signature.key_id` must equal both the
  requested anchor and the verify principal parsed from the embedded recipe; any
  divergence raises before an artifact is emitted, making the anchor/recipe
  mismatch class of bug impossible to ship.
- The Operator-held root-signing hard refusal is unchanged: staging still stops
  at the `<RESIGN-REQUIRED-ce-root-v1>` seam with no auto-signing.

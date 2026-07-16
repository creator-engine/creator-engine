---
slug: ce-559-release-smoke-evidence-gate
date: 2026-07-14
kind: story
scope: validators
issue: ce-ops#559
---

**Fail-closed release smoke-evidence gate.**

Implement the fail-closed release smoke-evidence PR-diff gate.

- Detect release-class changes only when the signed install spec and release-finalize manifest both change.
- Require one canonical, detached-SSHSIG-verified evidence record and the complete typed finalize-manifest contract, both bound to the checked-out spec.
- Wire the gate into both CI merge-queue/PR validation and local preflight, with hermetic focused tests.
- Add the governed post-PR producer path: digest-pinned no-checkout smoke result,
  canonical offline-signing bytes, public-only SSHSIG finalization, exact
  finalized-tree verification, and atomic evidence/carrier output.

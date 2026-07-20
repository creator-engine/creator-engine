---
slug: ce-root-rotation-succession-runbook
date: 2026-07-20
kind: added
scope: release-signing trust-root operations
---

**Add the CE root rotation and succession runbook.**

- Documents public consumer re-anchoring, normal succession, historical release
  reissue, compromise revocation, fail-closed behavior, and unrecoverable
  limits.
- Makes the installer-facing DNS TXT anchor and the revocation-to-re-anchoring
  fail-closed user experience explicit.
- Keeps signing and release actions controller-only and excludes private-key
  material and passphrases from the procedure.
- Records `docs/contracts/installer.md` as a deferred public consumer-contract
  update, with successor endpoint, DNS-anchor, and verification wording to be
  changed outside this documentation-only carrier.

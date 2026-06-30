---
slug: ce-366-main-head-resolver
date: 2026-06-30
kind: feature
scope: installer
issue: ce-ops#366/L1.a
---

**Verified main HEAD artifact resolver and clean install.**

- **Declared work class:** feature
- Add a fail-closed origin/main resolver that builds a first-party wheel from the resolved commit and verifies source/artifact hashes before promotion.
- Add `ce clean-main-install` and the `ce update --track main` seam without using ce-root-v1 release signing for main-head artifacts.
- Stabilize an existing Unix-socket unit test under `TMPDIR=/var/tmp` by using a short socket path.

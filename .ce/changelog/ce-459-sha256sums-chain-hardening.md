---
slug: ce-459-sha256sums-chain-hardening
date: 2026-07-06
kind: security
scope: client-ci
issue: ce-ops#459
---

**Harden adopted client SHA256SUMS verification.**

- Generated adopted-repo CI now verifies the signed CE install spec and out-of-band trust anchor before accepting the signed SHA256SUMS digest.
- Regression coverage asserts the previous direct SHA256SUMS download path is no longer emitted.

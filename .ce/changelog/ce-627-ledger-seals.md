---
slug: ce-627-ledger-seals
date: 2026-07-20
kind: changed
scope: side-effect ledger runtime
issue: ce-ops#627
---

**Explicit hash seals for the Side-Effect Ledger runtime.**

- New runtime records store the writer-owned `details.prev_seal_sha256` link
  and verification refuses broken, missing, reordered, or altered seals.
- Migration posture: existing unsealed ledgers remain valid. The first record
  appended by this runtime begins an explicit seal chain at the all-zero
  genesis sentinel; earlier records remain unsealed legacy history.
- A writer-owned CE627 seal-scheme marker distinguishes new seals from a
  caller-controlled legacy `prev_seal_sha256` detail, which remains ordinary
  legacy data and cannot start or break a seal chain.
- Regression coverage now separately proves both a missing writer marker after
  a sealed predecessor and writer overwrite of attacker-provided values for
  both reserved seal details.
- Consumers of written runtime records must treat `details.prev_seal_sha256`
  and `details._ce627_seal_scheme` as reserved writer-owned keys in addition
  to their caller-provided detail fields.
- The existing record-byte chain, head-manifest agreement, and append-only
  refusals remain in force alongside the additive explicit seal chain.

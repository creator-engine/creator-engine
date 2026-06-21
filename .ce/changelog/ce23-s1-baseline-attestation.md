---
slug: ce23-s1-baseline-attestation
date: 2026-06-21
kind: added
scope: brownfield baseline attestation
issue: ce-ops#23
base: 4693465d8760bad13ccfa230cc9b17022092e71f
---

Adds the Slice 1 brownfield baseline-attestation spine for no-history capture.

- Adds the value-free baseline-attestation schema with baseline commit SHA,
  snapshot content digest, clean scrub summary, attestor reference, timestamp,
  and canonical content digest.
- Adds a pure deterministic record builder in `v3_installer.py`.
- Registers a validator check that enforces schema, no secret-shaped values, and
  content-digest parity.
- Adds red-to-green unit coverage for schema shape, deterministic builder output,
  raw-finding refusal, and digest tamper detection.

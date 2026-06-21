---
slug: ce158-trust-anchor
date: 2026-06-21
kind: fixed
scope: v3 installer authentic verification
issue: ce-ops#158
base: d6ba7ee291c882aa865af7e0e32972b3223b5532
---

Require an out-of-band trust anchor before authentic onboarding can report the
served `ce-root-v1` trust root as verified.

- Added pure verifier helpers for OpenSSH SHA256 public-key fingerprints,
  out-of-band anchor record parsing, and anchor agreement evidence.
- Added `ce onboard --trust-anchor SOURCE=PATH` for authentic onboarding and
  fail-closed handling for same-origin-only or mismatched anchors.
- Surfaced agreeing anchor sources in machine-readable onboarding output.
- Documented the recommended DNS TXT primary anchor, defense-in-depth GitHub and
  Sigstore options, and the publish-side fingerprint record format.

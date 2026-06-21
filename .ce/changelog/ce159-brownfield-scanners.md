---
slug: ce159-brownfield-scanners
date: 2026-06-21
kind: fixed
scope: brownfield adoption scanner provisioning
issue: ce-ops#159
base: d6ba7ee291c882aa865af7e0e32972b3223b5532
---

Provision the brownfield secret-preflight scanners from sha256-pinned upstream
release archives so self-serve adoption no longer depends on user-supplied
scanner URLs.

- Populates the built-in Gitleaks and TruffleHog pins for Linux x86_64 and
  arm64 from reproduced upstream release archive hashes.
- Verifies the fetched archive bytes before extracting a single expected
  scanner binary member, then fail-closes on hash, extraction, or spawn errors.
- Updates the scanner manifest fragment to carry the release archive URL,
  sha256, version, platform, and archive member for each scanner.
- Adds regression coverage for non-empty default scanner pins, archive extraction,
  manifest parity, and hash-mismatch refusal.

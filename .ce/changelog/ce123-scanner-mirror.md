---
slug: ce123-scanner-mirror
date: 2026-06-18
kind: fixed
scope: brownfield secret preflight
issue: ce-ops#123
base: 8cc07222a8051b2c3e6804d92036680711928472
---

Commissions sha256-pinned Gitleaks and TruffleHog mirror artifacts for the
brownfield adoption secret preflight.

- Adds unsigned staged scanner mirror artifacts for Linux x86_64 and Linux
  arm64 under `docs/downloads/0.2.0/scanners/`.
- Adds `scanner-mirror.fragment.yaml` with `{name, version, platform, url,
  sha256}` entries for all four scanner/platform combinations; controller
  signing and Pages publish remain gated.
- Wires the live adoption driver to select commissioned scanner pins by host
  platform while preserving fail-closed behavior for unsupported platforms,
  incomplete env overrides, fetch failures, and sha256 mismatches.
- Keeps `CE_FORGE_GITLEAKS_*` and `CE_FORGE_TRUFFLEHOG_*` runtime commissioning
  overrides for pinned local or air-gapped scanner artifacts.
- Adds focused tests for x86_64 pinned-fetch clean, sha mismatch refusal,
  404/unpinned refusal, env commissioning, and arm64 manifest/hash resolution.

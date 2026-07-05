---
slug: ce-451-zeros-digest-guard
date: 2026-07-05
kind: tiny
scope: surfaces manifest placeholder digest guard
issue: creator-engine/ce-ops#451
---

**Reject placeholder surface sha256 digests.**

## Summary

- Reject all-identical sha256 placeholder digest strings as unpinned in the surfaces manifest consistency check.
- Keep legitimate mixed sha256 digests and the CE seat image `UNSET` allowlist behavior working.

## Validation

- `PYTHONPATH=validators python -m pytest validators/tests/unit/test_surfaces_manifest.py -q`
- `ce validate-pr --repo-root .`

- **Declared work class:** tiny

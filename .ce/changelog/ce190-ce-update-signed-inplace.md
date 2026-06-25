---
slug: ce190-ce-update-signed-inplace
date: 2026-06-25
kind: epic
scope: signed in-place CE updater
issue: ce-ops#190
---

**feat: first-class ce update.**

## Summary
- Add first-class `ce update` and `ce update --check` over the signed installer trust path.
- Verify signed spec, DNS trust anchor, SHA256SUMS, selected wheel bytes, and app wheel identity before any update mutation.
- Swap verified venv targets in place under the install lock, with rollback-aware promotion/state writes.

## Validation
- TMPDIR=/tmp validators/.venv/bin/python -m pytest validators/tests/unit
- validators/.venv/bin/python -m creator_engine_validator verify-work-sizing-floor --base origin/main --declared-work-class epic .
- validators/.venv/bin/python -m creator_engine_validator verify-path-manifest --base origin/main --manifest-dir .ce/pr-manifests --head-ref ce190-ce-update-signed-inplace --require-carrier .

- **Declared work class:** epic

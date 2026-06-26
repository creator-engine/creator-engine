---
slug: ce222-egress-fail-closed
date: 2026-06-26
kind: story
scope: gVisor egress attestation
issue: ce-ops#222
---

**Fail closed on unproven gVisor egress.**

- **Declared work class:** story

## Summary
- Add regression coverage that gVisor egress confinement is not claimed from metadata-only proxy hints.
- Add launch-path coverage that non-empty egress policy refuses before container start when enforcement is unproven.

## Validation
- `PYTHONPATH=validators /workspace/creator-engine/.venv/bin/python -m pytest validators/tests/unit/test_gvisor_proxy_backend.py validators/tests/unit/test_contained_launch_proof.py`
- `PYTHONPATH=validators /workspace/creator-engine/.venv/bin/python -m pytest validators/tests/unit`
